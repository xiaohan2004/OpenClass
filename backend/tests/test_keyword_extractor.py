"""
关键词提取功能测试
"""

import unittest
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.keyword_extraction_algorithm import KeywordExtractor, KeywordScore


class TestKeywordExtractor(unittest.TestCase):
    """关键词提取器测试"""

    @classmethod
    def setUpClass(cls):
        """初始化提取器"""
        cls.extractor = KeywordExtractor(
            top_n_tfidf=15,
            top_n_keybert=15,
            top_m_history=10,
            top_k_output=10,
        )

    def test_preprocess_text(self):
        """测试文本预处理"""
        text = "机器学习是人工智能的重要领域，包括监督学习和无监督学习"
        tokens = self.extractor.preprocess_text(text)

        self.assertTrue(len(tokens) > 0)
        self.assertNotIn("的", tokens)  # 停用词应被去除
        print(f"预处理结果：{tokens}")

    def test_build_ngrams(self):
        """测试n-gram构造"""
        tokens = ["机器", "学习", "是", "有", "趣", "的"]
        ngrams = self.extractor._build_ngrams(tokens)

        # 应包含unigram、bigram、trigram
        self.assertIn("机器", ngrams)
        self.assertIn("机器学习", ngrams)
        self.assertIn("机器学习是", ngrams)
        print(f"N-gram总数：{len(ngrams)}")

    def test_extract_tfidf_keywords(self):
        """测试TF-IDF关键词提取"""
        text = "深度学习使用神经网络进行特征学习，神经网络包含多层隐藏层"
        tokens = self.extractor.preprocess_text(text)
        ngrams = self.extractor._build_ngrams(tokens)

        tfidf_dict = self.extractor._extract_tfidf_keywords(text, ngrams)

        self.assertTrue(len(tfidf_dict) > 0)
        # 检查分数范围
        for score in tfidf_dict.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

        print(f"TF-IDF关键词（Top {len(tfidf_dict)}）：")
        for word, score in sorted(tfidf_dict.items(), key=lambda x: x[1], reverse=True):
            print(f"  {word}: {score:.4f}")

    def test_extract_history_keywords(self):
        """测试历史关键词提取"""
        history = (
            "课堂前半部分介绍了Python基础知识，包括数据类型、函数定义和面向对象编程"
        )
        keywords = self.extractor._extract_history_keywords(history)

        self.assertTrue(len(keywords) > 0)
        print(f"历史关键词：{keywords}")

    def test_extract_history_keywords_empty(self):
        """测试历史关键词提取（空输入）"""
        keywords = self.extractor._extract_history_keywords("")
        self.assertEqual(len(keywords), 0)

        keywords = self.extractor._extract_history_keywords(None)
        self.assertEqual(len(keywords), 0)

    def test_compute_embeddings(self):
        """测试embedding计算"""
        words = ["机器学习", "深度学习", "神经网络", "数据科学"]
        embeddings = self.extractor._compute_embeddings(words)

        self.assertEqual(len(embeddings), len(words))
        expected_dim = len(self.extractor.embedding_model.encode(["测试"])[0])
        for word, emb in embeddings.items():
            self.assertIsNotNone(emb)
            self.assertEqual(len(emb), expected_dim)

        print(f"Embedding维度：{expected_dim}")

    def test_compute_history_similarity_empty_history(self):
        """测试历史相似度计算（空历史）"""
        candidates = {
            "机器学习": self.extractor.embedding_model.encode(["机器学习"])[0],
            "深度学习": self.extractor.embedding_model.encode(["深度学习"])[0],
        }

        similarities = self.extractor._compute_history_similarity(candidates, {})

        # 当历史为空时，相似度应全为0
        for sim in similarities.values():
            self.assertEqual(sim, 0.0)

    def test_extract_keywords_simple(self):
        """测试完整的关键词提取流程（简单case）"""
        transcript = "数据科学使用统计学、编程和机器学习来分析大规模数据集。数据科学家需要掌握Python编程、统计学和机器学习算法。"

        results = self.extractor.extract_keywords(transcript)

        self.assertTrue(len(results) > 0)
        self.assertLessEqual(len(results), self.extractor.top_k_output)

        # 检查返回类型和分数范围
        for result in results:
            self.assertIsInstance(result, KeywordScore)
            self.assertGreaterEqual(result.final_score, 0.0)
            self.assertLessEqual(result.final_score, 1.0)

        print(f"提取的关键词（Top {len(results)}）：")
        for r in results:
            print(
                f"  {r.keyword}: {r.final_score:.4f} "
                f"(tf-idf={r.tfidf_score:.4f}, keybert={r.keybert_score:.4f}, "
                f"history_sim={r.history_sim:.4f}, novelty={r.novelty_score:.4f})"
            )

    def test_extract_keywords_with_history(self):
        """测试完整的关键词提取流程（含历史摘要）"""
        transcript = "今天我们继续讨论机器学习中的分类和回归问题。分类任务是预测离散的类别标签，而回归任务是预测连续的数值。常见的分类算法包括决策树、随机森林和支持向量机。"
        history = "前面课程介绍了机器学习的基本概念，包括监督学习、无监督学习和强化学习的定义。"

        results = self.extractor.extract_keywords(transcript, history)

        self.assertTrue(len(results) > 0)
        print(f"\n含历史摘要的关键词提取（Top {len(results)}）：")
        for r in results:
            print(
                f"  {r.keyword}: {r.final_score:.4f} "
                f"(novelty={r.novelty_score:.4f}, history_sim={r.history_sim:.4f})"
            )

    def test_extract_keywords_empty_transcript(self):
        """测试空讲解文本的处理"""
        results = self.extractor.extract_keywords("")
        self.assertEqual(len(results), 0)

        results = self.extractor.extract_keywords(None)
        self.assertEqual(len(results), 0)

    def test_extract_keywords_with_details(self):
        """测试返回详细信息的提取方法"""
        transcript = "自然语言处理是人工智能的重要分支，包括文本分类、情感分析、机器翻译和问答系统。"

        details = self.extractor.extract_keywords_with_details(transcript)

        self.assertIn("keywords", details)
        self.assertIn("details", details)
        self.assertEqual(len(details["keywords"]), len(details["details"]))

        print(f"\n关键词详细信息：")
        print(f"关键词列表：{details['keywords']}")
        for detail in details["details"][:3]:
            print(f"  {detail['keyword']}: {detail['final_score']}")

    def test_keyword_order(self):
        """测试关键词是否按分数降序排列"""
        transcript = "深度学习神经网络卷积神经网络循环神经网络Transformer注意力机制"

        results = self.extractor.extract_keywords(transcript)

        # 检查分数是否递减
        for i in range(len(results) - 1):
            self.assertGreaterEqual(
                results[i].final_score,
                results[i + 1].final_score,
                f"关键词未按分数递减排序：{results[i].keyword} ({results[i].final_score}) "
                f"> {results[i + 1].keyword} ({results[i + 1].final_score})",
            )


if __name__ == "__main__":
    unittest.main()
