"""
核心业务逻辑 - 关键词提取处理器

基于统一课堂上下文，实现多策略关键词提取和排序

停用词表：从 data/stopwords.txt 文件加载（包含 2991 个停用词，包括 1513 个中文词）
备用停用词：如果文件不存在，使用内嵌的默认停用词表
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import jieba
import numpy as np
from keybert import KeyBERT
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer

from app.utils.model_download_policy import get_keyword_model_download_allowed

logger = logging.getLogger(__name__)


def _load_stopwords() -> set[str]:
    """从 data/stopwords.txt 读取停用词"""
    try:
        # 尝试找到 stopwords.txt 文件
        # 优先查找：1. backend/data/stopwords.txt
        #          2. project_root/data/stopwords.txt（备选）
        possible_paths = [
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "stopwords.txt",  # project_root/data
            Path(__file__).parent.parent.parent
            / "data"
            / "stopwords.txt",  # backend/data
        ]

        stopwords_file = None
        for path in possible_paths:
            if path.exists():
                stopwords_file = path
                break

        if stopwords_file is None:
            logger.warning("未找到 stopwords.txt 文件，使用默认停用词表")
            return _get_default_stopwords()

        stopwords = set()
        with open(stopwords_file, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith("#"):  # 跳过空行和注释
                    stopwords.add(word)

        logger.info("从 %s 加载了 %d 个停用词", stopwords_file, len(stopwords))
        return stopwords

    except Exception as e:
        logger.error("读取 stopwords.txt 失败: %s，使用默认停用词表", e)
        return _get_default_stopwords()


def _get_default_stopwords() -> set[str]:
    """默认的中文停用词表 - 包含口语词、虚词、助词等"""
    return {
        "的",
        "了",
        "和",
        "是",
        "就",
        "都",
        "而",
        "及",
        "在",
        "为",
        "有",
        "被",
        "要",
        "不",
        "人",
        "这",
        "中",
        "大",
        "来",
        "上",
        "小",
        "多",
        "然后",
        "就是",
        "嗯",
        "呃",
        "对",
        "好",
        "你",
        "我",
        "他",
        "她",
        "它",
        "这个",
        "那个",
        "一个",
        "两个",
        "很",
        "还",
        "也",
        "又",
        "可",
        "可以",
        "能",
        "能够",
        "可能",
        "应该",
        "必须",
        "需要",
        "想要",
        "不过",
        "但是",
        "然而",
        "因为",
        "所以",
        "如果",
        "那么",
        "否则",
        "而且",
        "或者",
        "只有",
        "只要",
        "除非",
        "除了",
        "比如",
        "例如",
        "等等",
        "以及",
        "与其",
        "其中",
        "其实",
        "实际上",
        "让我",
        "告诉",
        "说说",
        "讲讲",
        "呢",
        "啊",
        "哦",
        "吗",
        "的话",
        "呀",
        "呢",
        "啦",
        "呗",
        "哈",
        "嘿",
        "嘛",
        "哼",
        "嘟",
        "吧",
        "罢了",
        "而已",
        "之外",
        "以下",
        "以上",
        "相比",
        "相对",
        "相同",
        "相似",
        "不同",
        "不一样",
    }


# 加载停用词表
STOPWORDS = _load_stopwords()


@dataclass
class KeywordScore:
    """关键词及其各项分数"""

    keyword: str
    tfidf_score: float = 0.0
    keybert_score: float = 0.0
    history_sim: float = 0.0
    novelty_score: float = 0.0
    final_score: float = 0.0


class KeywordExtractor:
    """
    关键词提取处理器

    基于 TF-IDF、KeyBERT 和 embedding 相似度的多策略关键词提取
    支持历史要点摘要的冷启动处理
    """

    def __init__(
        self,
        embedding_model: str = "shibing624/text2vec-base-chinese",
        top_n_tfidf: int = 20,
        top_n_keybert: int = 20,
        top_m_history: int = 15,
        top_k_output: int = 10,
        clustering_threshold: float = 0.85,
        n_clusters: Optional[int] = None,
    ):
        """
        初始化关键词提取器

        Args:
            embedding_model: sentence-transformers 模型名称（默认：中文优化模型）
            top_n_tfidf: TF-IDF提取的Top-N词数
            top_n_keybert: KeyBERT提取的Top-N词数
            top_m_history: 历史摘要提取的Top-M词数
            top_k_output: 最终输出的Top-K词数
            clustering_threshold: 聚类相似度阈值
            n_clusters: KMeans聚类数（若为None则根据候选词数自动计算）
        """
        self.top_n_tfidf = top_n_tfidf
        self.top_n_keybert = top_n_keybert
        self.top_m_history = top_m_history
        self.top_k_output = top_k_output
        self.clustering_threshold = clustering_threshold
        self.n_clusters = n_clusters

        logger.info("初始化KeywordExtractor：embedding模型=%s", embedding_model)
        allow_model_download = get_keyword_model_download_allowed()
        local_files_only = not allow_model_download
        logger.info(
            "关键词模型加载策略：%s",
            "允许联网下载" if allow_model_download else "仅使用本地缓存",
        )
        # 尝试加载中文优化模型，失败时降级到 all-MiniLM-L6-v2
        try:
            self.embedding_model = SentenceTransformer(
                embedding_model,
                local_files_only=local_files_only,
            )
        except Exception as e:
            logger.warning("加载中文模型失败(%s)，降级到英文模型", e)
            try:
                self.embedding_model = SentenceTransformer(
                    "all-MiniLM-L6-v2",
                    local_files_only=local_files_only,
                )
            except Exception as fallback_exc:
                if allow_model_download:
                    raise
                raise RuntimeError(
                    "本地模型缓存不可用，且当前启动已选择不联网下载"
                ) from fallback_exc

        self.keybert_model = KeyBERT(model=self.embedding_model)
        logger.info("KeywordExtractor 初始化完成")

    def preprocess_text(self, text: str) -> list[str]:
        """
        文本预处理：分词、去停用词、过滤短词

        Args:
            text: 原始文本

        Returns:
            处理后的词列表
        """
        # 中文分词
        tokens = jieba.cut(text.strip(), cut_all=False)

        # 去停用词、过滤长度≤1的词
        filtered = [
            token.strip()
            for token in tokens
            if len(token.strip()) > 1 and token.strip() not in STOPWORDS
        ]

        return filtered

    def _build_ngrams(self, tokens: list[str]) -> list[str]:
        """
        构造 unigram、bigram、trigram（去重版本）

        Args:
            tokens: 分词结果

        Returns:
            去重后的 n-gram 词列表
        """
        ngrams = list(tokens)  # unigrams

        # bigrams
        for i in range(len(tokens) - 1):
            ngrams.append(tokens[i] + tokens[i + 1])

        # trigrams
        for i in range(len(tokens) - 2):
            ngrams.append(tokens[i] + tokens[i + 1] + tokens[i + 2])

        # 使用 dict.fromkeys 保持顺序并去重
        return list(dict.fromkeys(ngrams))

    def _extract_tfidf_keywords(self, text: str, ngrams: list[str]) -> dict[str, float]:
        """
        使用TF-IDF提取Top-N高频词

        Args:
            text: 原始文本
            ngrams: n-gram词列表（已去重）

        Returns:
            {词: 分数} 的字典，分数归一化到0~1
        """
        if not ngrams or not text:
            return {}

        try:
            unique_vocab = list(dict.fromkeys(ngrams))

            logger.debug(
                "TF-IDF词表大小：%d（去重前：%d）", len(unique_vocab), len(ngrams)
            )

            tokens = self.preprocess_text(text)
            if not tokens:
                return {}

            all_ngrams = list(tokens)
            for i in range(len(tokens) - 1):
                all_ngrams.append(tokens[i] + tokens[i + 1])
            for i in range(len(tokens) - 2):
                all_ngrams.append(tokens[i] + tokens[i + 1] + tokens[i + 2])

            vectorizer = TfidfVectorizer(
                vocabulary=unique_vocab,
                analyzer=str.split,
                norm="l2",
                min_df=1,
                max_df=1.0,
                lowercase=False,
                token_pattern=None,
            )
            tfidf_matrix = vectorizer.fit_transform([" ".join(all_ngrams)])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]

            # 获取Top-N
            top_indices = np.argsort(scores)[-self.top_n_tfidf :][::-1]
            tfidf_dict = {
                feature_names[i]: float(scores[i]) for i in top_indices if scores[i] > 0
            }

            # 归一化到0~1
            if tfidf_dict:
                max_score = max(tfidf_dict.values())
                tfidf_dict = {
                    k: v / max_score if max_score > 0 else 0
                    for k, v in tfidf_dict.items()
                }

            logger.debug("TF-IDF提取了%d个关键词", len(tfidf_dict))
            return tfidf_dict

        except Exception as e:
            logger.error("TF-IDF提取失败: %s", e)
            return {}

    def _extract_keybert_keywords(self, text: str) -> dict[str, float]:
        """
        使用KeyBERT提取语义关键词Top-N（中文优化版）

        Args:
            text: 原始文本

        Returns:
            {词: 分数} 的字典，分数已归一化到0~1
        """
        if not text:
            return {}

        try:
            # 中文文本预处理：分词后拼接，让 KeyBERT 能更好地识别
            tokens = jieba.cut(text.strip(), cut_all=False)
            processed_text = " ".join(tokens)

            # 限制 n-gram 范围为 1-2，避免抽取整句
            keywords = self.keybert_model.extract_keywords(
                processed_text,
                keyphrase_ngram_range=(1, 2),  # 限制为单词和两字词
                stop_words=None,  # 停用词已在预处理中处理
                top_n=self.top_n_keybert,
                use_mmr=True,
                diversity=0.5,
            )

            keybert_dict = {kw: float(score) for kw, score in keywords}
            logger.debug("KeyBERT提取了%d个关键词", len(keybert_dict))
            return keybert_dict

        except Exception as e:
            logger.error("KeyBERT提取失败: %s", e)
            return {}

    def _merge_candidates(
        self,
        tfidf_dict: dict[str, float],
        keybert_dict: dict[str, float],
    ) -> dict[str, tuple[float, float]]:
        """
        合并TF-IDF和KeyBERT结果，去重

        Returns:
            {词: (tfidf_score, keybert_score)} 的字典
        """
        candidates = {}

        for word, score in tfidf_dict.items():
            candidates[word] = (score, 0.0)

        for word, score in keybert_dict.items():
            if word in candidates:
                tfidf_score, _ = candidates[word]
                candidates[word] = (tfidf_score, score)
            else:
                candidates[word] = (0.0, score)

        return candidates

    def _extract_history_keywords(self, history_summary: str) -> list[str]:
        """
        从历史要点摘要中提取关键词

        Args:
            history_summary: 历史要点摘要文本

        Returns:
            历史关键词列表
        """
        if not history_summary:
            return []

        try:
            tokens = self.preprocess_text(history_summary)
            ngrams = self._build_ngrams(tokens)
            history_dict = self._extract_tfidf_keywords(history_summary, ngrams)
            return list(history_dict.keys())

        except Exception as e:
            logger.error("历史关键词提取失败: %s", e)
            return []

    def _compute_embeddings(self, words: list[str]) -> dict[str, np.ndarray]:
        """
        计算词的embedding向量

        Args:
            words: 词列表

        Returns:
            {词: embedding向量} 的字典
        """
        if not words:
            return {}

        try:
            embeddings = self.embedding_model.encode(words, show_progress_bar=False)
            return {word: embedding for word, embedding in zip(words, embeddings)}

        except Exception as e:
            logger.error("Embedding计算失败: %s", e)
            return {}

    def _compute_history_similarity(
        self,
        candidate_embeddings: dict[str, np.ndarray],
        history_embeddings: dict[str, np.ndarray],
    ) -> dict[str, float]:
        """
        计算每个候选词与历史词的最大余弦相似度

        Args:
            candidate_embeddings: 候选词的embedding
            history_embeddings: 历史词的embedding

        Returns:
            {候选词: 最大相似度} 的字典
        """
        similarities = {}

        if not history_embeddings:
            # 历史为空，所有词的相似度为0
            return {word: 0.0 for word in candidate_embeddings.keys()}

        for candidate, emb_c in candidate_embeddings.items():
            max_sim = 0.0
            for history_word, emb_h in history_embeddings.items():
                # 余弦相似度 = 1 - cosine距离
                sim = 1 - cosine(emb_c, emb_h)
                max_sim = max(max_sim, sim)

            similarities[candidate] = max(0.0, min(1.0, max_sim))

        return similarities

    def _cluster_and_deduplicate(
        self,
        candidates: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:
        """
        基于embedding的聚类去重，每个cluster保留最接近中心的词

        Args:
            candidates: {词: embedding向量} 的字典

        Returns:
            去重后的 {词: embedding向量} 的字典
        """
        if len(candidates) <= 1:
            return candidates

        try:
            words = list(candidates.keys())
            embeddings = np.array([candidates[w] for w in words])

            # 自动计算聚类数
            n_clusters = self.n_clusters
            if n_clusters is None:
                n_clusters = max(1, len(words) // 3)  # 粗略启发式
            else:
                n_clusters = min(n_clusters, len(words))

            if n_clusters == 1:
                return candidates

            # KMeans聚类
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            # 每个cluster保留最接近中心的词
            result = {}
            centers = kmeans.cluster_centers_

            for cluster_id in range(n_clusters):
                cluster_indices = np.where(labels == cluster_id)[0]
                if len(cluster_indices) == 0:
                    continue

                # 计算每个词与中心的距离
                distances = [
                    np.linalg.norm(embeddings[i] - centers[cluster_id])
                    for i in cluster_indices
                ]

                # 选择最近的词
                best_idx = cluster_indices[np.argmin(distances)]
                best_word = words[best_idx]
                result[best_word] = embeddings[best_idx]

            logger.debug("聚类去重：%d个词 -> %d个词", len(candidates), len(result))
            return result

        except Exception as e:
            logger.error("聚类失败，返回原始候选词: %s", e)
            return candidates

    def _compute_final_scores(
        self,
        candidates: dict[str, tuple[float, float]],
        history_sim: dict[str, float],
        weight_tfidf: float = 0.3,
        weight_keybert: float = 0.3,
        weight_history_sim: float = 0.2,
        weight_novelty: float = 0.2,
    ) -> list[KeywordScore]:
        """
        计算最终得分

        Args:
            candidates: {词: (tfidf_score, keybert_score)}
            history_sim: {词: 历史相似度}
            weight_*: 各项权重

        Returns:
            KeywordScore列表（已按分数降序排序）
        """
        scores = []

        for word, (tfidf_score, keybert_score) in candidates.items():
            hist_sim = history_sim.get(word, 0.0)
            novelty = 1.0 - hist_sim  # 新颖性 = 1 - history_sim

            final_score = (
                weight_tfidf * tfidf_score
                + weight_keybert * keybert_score
                + weight_history_sim * hist_sim
                + weight_novelty * novelty
            )

            scores.append(
                KeywordScore(
                    keyword=word,
                    tfidf_score=tfidf_score,
                    keybert_score=keybert_score,
                    history_sim=hist_sim,
                    novelty_score=novelty,
                    final_score=final_score,
                )
            )

        # 按最终分数降序排序
        scores.sort(key=lambda x: x.final_score, reverse=True)
        return scores

    def extract_keywords(
        self,
        transcript: str,
        history_summary: Optional[str] = None,
    ) -> list[KeywordScore]:
        """
        提取关键词

        Args:
            transcript: 近期讲解文本（课堂语音转写文本，可能存在噪声）
            history_summary: 历史要点摘要（可选，为空时自动降级为纯关键词提取）

        Returns:
            KeywordScore列表，按最终分数降序排序，长度不超过top_k_output
        """
        if not transcript:
            logger.warning("输入的讲解文本为空")
            return []

        logger.info("开始提取关键词，transcript长度=%d", len(transcript))

        # 1. 文本预处理
        tokens = self.preprocess_text(transcript)
        logger.debug("分词完成：%d个词", len(tokens))

        if not tokens:
            logger.warning("分词后无有效词，跳过关键词提取")
            return []

        ngrams = self._build_ngrams(tokens)
        logger.debug("构造n-gram完成：%d个n-gram", len(ngrams))

        # 2. 候选关键词提取
        tfidf_dict = self._extract_tfidf_keywords(transcript, ngrams)
        keybert_dict = self._extract_keybert_keywords(transcript)

        candidates = self._merge_candidates(tfidf_dict, keybert_dict)
        logger.info("合并后得到%d个候选关键词", len(candidates))

        if not candidates:
            logger.warning("无法提取有效的候选关键词")
            return []

        # 3. 处理历史要点摘要
        history_keywords = self._extract_history_keywords(history_summary)
        logger.info(
            "历史摘要提取%d个关键词",
            len(history_keywords),
        )

        # 4. 计算embedding
        all_words = list(candidates.keys()) + history_keywords
        all_embeddings = self._compute_embeddings(all_words)

        candidate_embeddings = {
            w: all_embeddings[w] for w in candidates.keys() if w in all_embeddings
        }
        history_embeddings = {
            w: all_embeddings[w] for w in history_keywords if w in all_embeddings
        }

        logger.debug("Embedding计算完成：%d个词", len(all_embeddings))

        # 5. 计算历史相似度
        history_sim = self._compute_history_similarity(
            candidate_embeddings,
            history_embeddings,
        )
        logger.debug("历史相似度计算完成")

        # 6. 基于embedding的聚类去重
        deduplicated = self._cluster_and_deduplicate(candidate_embeddings)

        # 更新candidates为去重后的版本
        candidates_deduplicated = {
            word: candidates[word] for word in deduplicated.keys()
        }

        # 7. 计算最终得分并排序
        keyword_scores = self._compute_final_scores(
            candidates_deduplicated, history_sim
        )

        # 8. 返回Top-K
        result = keyword_scores[: self.top_k_output]
        logger.info("最终输出%d个关键词", len(result))

        return result

    def extract_keywords_with_details(
        self,
        transcript: str,
        history_summary: Optional[str] = None,
    ) -> dict:
        """
        提取关键词并返回详细的调试信息

        Args:
            transcript: 近期讲解文本
            history_summary: 历史要点摘要

        Returns:
            包含关键词列表和调试信息的字典
        """
        scores = self.extract_keywords(transcript, history_summary)

        return {
            "keywords": [s.keyword for s in scores],
            "details": [
                {
                    "keyword": s.keyword,
                    "tfidf_score": round(s.tfidf_score, 4),
                    "keybert_score": round(s.keybert_score, 4),
                    "history_sim": round(s.history_sim, 4),
                    "novelty_score": round(s.novelty_score, 4),
                    "final_score": round(s.final_score, 4),
                }
                for s in scores
            ],
        }
