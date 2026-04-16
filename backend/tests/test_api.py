"""API 测试。"""

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import httpx
from sqlmodel import Session

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app.config as app_config
import app.db.session as db_session_module
from app.db import init_db
from app.db.crud import (
    create_course,
    create_question,
    create_relay_log,
    create_segment_summary,
    create_session,
    create_stats_hourly,
    create_stats_total,
    create_transcript,
    upsert_stats_daily,
)
from app.main import app


class TestAPI(unittest.TestCase):
    """FastAPI 接口测试。"""

    async def _request(self, method: str, path: str, json: dict | None = None):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, json=json)

    def request(self, method: str, path: str, json: dict | None = None):
        return asyncio.run(self._request(method, path, json=json))

    def setUp(self):
        """为每个测试准备独立数据库。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_api.db"
        self.db_url = f"sqlite:///{self.db_path.as_posix()}"

        self.env_patcher = mock.patch.dict(
            os.environ,
            {"DATABASE_URL": self.db_url, "DATABASE_ECHO": "false"},
            clear=False,
        )
        self.env_patcher.start()

        app_config.get_settings.cache_clear()
        db_session_module.get_engine.cache_clear()
        db_session_module.engine = db_session_module.get_engine()
        init_db()
        self.seed_data = self._seed_data()

    def tearDown(self):
        """清理环境。"""
        db_session_module.get_engine().dispose()
        self.env_patcher.stop()
        app_config.get_settings.cache_clear()
        db_session_module.get_engine.cache_clear()
        self.temp_dir.cleanup()

    def _seed_data(self):
        """准备一组基础测试数据。"""
        with Session(db_session_module.get_engine()) as db:
            course = create_course(
                db,
                code="MATH101",
                name="高等数学",
                description="极限与导数",
                teacher="张老师",
            )
            session = create_session(
                db,
                course_id=course.id,
                title="第一节：极限",
            )
            transcript = create_transcript(
                db,
                session.id,
                "这是转写内容",
                seq=1,
                start_time=1712995200,
                end_time=1712995210,
            )
            question = create_question(db, session.id, "这里为什么这样做？", score=0.8)
            summary = create_segment_summary(
                db,
                session.id,
                "这是分段小结",
                start_time=1712995200,
                end_time=1712995300,
                score=0.9,
            )
            relay_log = create_relay_log(
                db,
                time=1712995200,
                service_type="llm",
                request_model_name="deepseek-chat",
                input_value=12,
                output_value=34,
                latency=200,
                status="success",
            )
            stats_total = create_stats_total(
                db, service_type="llm", input_value=100, output_value=50
            )
            upsert_stats_daily(db, "2026-04-13", "llm", input_value=60, output_value=30)
            create_stats_hourly(
                db, "2026-04-13", 8, "llm", input_value=10, output_value=5
            )

            return {
                "course_id": course.id,
                "session_id": session.id,
                "transcript_id": transcript.id,
                "question_id": question.id,
                "summary_id": summary.id,
                "relay_log_id": relay_log.id,
                "stats_total_id": stats_total.id,
            }

    def test_health_check_endpoint(self):
        """健康检查接口应正常返回。"""
        response = self.request("GET", "/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "message": "服务正常运行"})

    def test_app_initialization(self):
        """应用应正确初始化。"""
        self.assertIsNotNone(app)
        self.assertEqual(app.title, "OpenClass - 课堂模拟学生提问助手")

    def test_health_check_with_different_methods(self):
        """健康检查仅允许 GET。"""
        self.assertEqual(self.request("GET", "/health").status_code, 200)
        self.assertEqual(self.request("POST", "/health").status_code, 405)
        self.assertEqual(self.request("PUT", "/health").status_code, 405)

    def test_nonexistent_endpoint(self):
        """不存在的端点应返回 404。"""
        response = self.request("GET", "/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_health_check_performance(self):
        """健康检查接口应足够快。"""
        start = time.time()
        response = self.request("GET", "/health")
        duration = time.time() - start

        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 1.0)

    def test_websocket_route_registered(self):
        """WebSocket 路由应已注册。"""
        websocket_routes = [
            route
            for route in app.routes
            if hasattr(route, "path") and "ws" in route.path
        ]
        self.assertGreater(len(websocket_routes), 0)

        ws_paths = {route.path for route in websocket_routes if hasattr(route, "path")}
        self.assertIn("/ws/session/{session_id}", ws_paths)

    def test_course_crud_endpoints(self):
        """课程 CRUD 接口应可用。"""
        create_response = self.request(
            "POST",
            "/api/courses",
            json={
                "code": "PHYS101",
                "name": "大学物理",
                "description": "力学基础",
                "teacher": "李老师",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        created_course = create_response.json()["data"]
        self.assertEqual(create_response.json()["msg"], "创建成功")
        self.assertEqual(created_course["code"], "PHYS101")

        list_response = self.request("GET", "/api/courses")
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(len(list_response.json()["data"]), 2)

        get_response = self.request("GET", f"/api/courses/{created_course['id']}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["data"]["name"], "大学物理")

        put_response = self.request(
            "PUT",
            f"/api/courses/{created_course['id']}",
            json={
                "code": "PHYS101",
                "name": "大学物理（更新）",
                "description": "力学与电磁学",
                "teacher": "李老师",
            },
        )
        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(put_response.json()["data"]["name"], "大学物理（更新）")

        patch_response = self.request(
            "PATCH",
            f"/api/courses/{created_course['id']}",
            json={"description": "本学期重点：力学"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(
            patch_response.json()["data"]["description"], "本学期重点：力学"
        )

        delete_response = self.request("DELETE", f"/api/courses/{created_course['id']}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["data"], {})

    def test_session_endpoints_follow_project_plan(self):
        """课堂与控制接口应符合计划中的行为。"""
        create_response = self.request(
            "POST",
            "/api/sessions",
            json={
                "course_id": self.seed_data["course_id"],
                "title": "第二节：连续",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        created_session = create_response.json()["data"]
        self.assertIsNone(created_session["start_time"])
        self.assertEqual(created_session["seq"], 2)
        self.assertNotIn("config", created_session)

        list_response = self.request("GET", "/api/sessions")
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(len(list_response.json()["data"]), 2)

        by_course_response = self.request(
            "GET", f"/api/courses/{self.seed_data['course_id']}/sessions"
        )
        self.assertEqual(by_course_response.status_code, 200)
        self.assertGreaterEqual(len(by_course_response.json()["data"]), 2)

        put_response = self.request(
            "PUT",
            f"/api/sessions/{created_session['id']}",
            json={
                "title": "第二节：函数连续性",
            },
        )
        self.assertEqual(put_response.status_code, 200)
        self.assertEqual(put_response.json()["data"]["title"], "第二节：函数连续性")

        patch_response = self.request(
            "PATCH",
            f"/api/sessions/{created_session['id']}",
            json={"title": "第二节：极限与连续"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["data"]["title"], "第二节：极限与连续")

        start_response = self.request(
            "POST",
            f"/api/sessions/{created_session['id']}/start",
            json={"start_time": 1712995200},
        )
        self.assertEqual(start_response.status_code, 200)
        self.assertEqual(start_response.json()["msg"], "课堂已开始")

        get_started_response = self.request(
            "GET", f"/api/sessions/{created_session['id']}"
        )
        self.assertEqual(get_started_response.json()["data"]["start_time"], 1712995200)

        pause_response = self.request(
            "POST", f"/api/sessions/{created_session['id']}/pause"
        )
        self.assertEqual(pause_response.status_code, 200)
        self.assertEqual(pause_response.json()["msg"], "课堂已暂停")

        end_response = self.request(
            "POST",
            f"/api/sessions/{created_session['id']}/end",
            json={"end_time": 1713002400},
        )
        self.assertEqual(end_response.status_code, 200)
        self.assertEqual(end_response.json()["msg"], "课堂已结束")

        get_ended_response = self.request(
            "GET", f"/api/sessions/{created_session['id']}"
        )
        self.assertEqual(get_ended_response.json()["data"]["end_time"], 1713002400)

        delete_response = self.request(
            "DELETE", f"/api/sessions/{created_session['id']}"
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["data"], {})

    def test_readonly_resource_endpoints(self):
        """转写、问题、小结、日志与统计接口应可查询。"""
        transcript_response = self.request("GET", "/api/transcripts")
        self.assertEqual(transcript_response.status_code, 200)
        self.assertEqual(
            transcript_response.json()["data"][0]["id"], self.seed_data["transcript_id"]
        )

        transcript_detail = self.request(
            "GET", f"/api/transcripts/{self.seed_data['transcript_id']}"
        )
        self.assertEqual(transcript_detail.status_code, 200)
        self.assertEqual(transcript_detail.json()["data"]["text"], "这是转写内容")

        transcript_by_session = self.request(
            "GET", f"/api/sessions/{self.seed_data['session_id']}/transcripts"
        )
        self.assertEqual(transcript_by_session.status_code, 200)
        self.assertEqual(len(transcript_by_session.json()["data"]), 1)

        questions_response = self.request("GET", "/api/questions")
        self.assertEqual(questions_response.status_code, 200)
        self.assertEqual(
            questions_response.json()["data"][0]["id"], self.seed_data["question_id"]
        )

        question_patch_response = self.request(
            "PATCH",
            f"/api/questions/{self.seed_data['question_id']}",
            json={"status": "asked", "asked_at": 1712995600},
        )
        self.assertEqual(question_patch_response.status_code, 200)
        self.assertEqual(question_patch_response.json()["data"]["status"], "asked")
        self.assertEqual(question_patch_response.json()["data"]["asked_at"], 1712995600)

        question_by_session = self.request(
            "GET", f"/api/sessions/{self.seed_data['session_id']}/questions"
        )
        self.assertEqual(question_by_session.status_code, 200)
        self.assertEqual(len(question_by_session.json()["data"]), 1)

        summaries_response = self.request("GET", "/api/segment-summaries")
        self.assertEqual(summaries_response.status_code, 200)
        self.assertEqual(
            summaries_response.json()["data"][0]["id"], self.seed_data["summary_id"]
        )

        summary_detail = self.request(
            "GET", f"/api/segment-summaries/{self.seed_data['summary_id']}"
        )
        self.assertEqual(summary_detail.status_code, 200)
        self.assertEqual(summary_detail.json()["data"]["text"], "这是分段小结")

        summary_by_session = self.request(
            "GET", f"/api/sessions/{self.seed_data['session_id']}/segment-summaries"
        )
        self.assertEqual(summary_by_session.status_code, 200)
        self.assertEqual(len(summary_by_session.json()["data"]), 1)

        relay_logs_response = self.request("GET", "/api/relay-logs")
        self.assertEqual(relay_logs_response.status_code, 200)
        self.assertEqual(
            relay_logs_response.json()["data"][0]["id"], self.seed_data["relay_log_id"]
        )

        relay_log_detail = self.request(
            "GET", f"/api/relay-logs/{self.seed_data['relay_log_id']}"
        )
        self.assertEqual(relay_log_detail.status_code, 200)
        self.assertEqual(relay_log_detail.json()["data"]["service_type"], "llm")

        stats_totals_response = self.request("GET", "/api/stats/totals")
        self.assertEqual(stats_totals_response.status_code, 200)
        self.assertEqual(
            stats_totals_response.json()["data"][0]["id"],
            self.seed_data["stats_total_id"],
        )
        self.assertEqual(stats_totals_response.json()["data"][0]["service_type"], "llm")

        stats_dailies_response = self.request("GET", "/api/stats/dailies")
        self.assertEqual(stats_dailies_response.status_code, 200)
        self.assertEqual(stats_dailies_response.json()["data"][0]["date"], "2026-04-13")
        self.assertEqual(
            stats_dailies_response.json()["data"][0]["service_type"], "llm"
        )

        stats_hourlies_response = self.request("GET", "/api/stats/hourlies")
        self.assertEqual(stats_hourlies_response.status_code, 200)
        self.assertEqual(
            stats_hourlies_response.json()["data"][0]["date"], "2026-04-13"
        )
        self.assertEqual(
            stats_hourlies_response.json()["data"][0]["service_type"], "llm"
        )

    def test_settings_endpoints(self):
        """设置接口应支持读取与更新。"""
        get_response = self.request("GET", "/api/settings")
        self.assertEqual(get_response.status_code, 200)

        items = get_response.json()["data"]["items"]
        self.assertGreater(len(items), 0)

        base_url_item = next(
            item for item in items if item["key"] == "deepseek_base_url"
        )
        self.assertEqual(base_url_item["value"], "https://api.deepseek.com")
        self.assertEqual(base_url_item["sensitive"], False)

        sensitive_item = next(
            item for item in items if item["key"] == "deepseek_api_key"
        )
        self.assertEqual(sensitive_item["value"], None)
        self.assertEqual(sensitive_item["sensitive"], True)

        patch_response = self.request(
            "PATCH",
            "/api/settings",
            json={
                "items": [
                    {"key": "deepseek_base_url", "value": "https://custom.example.com"},
                    {"key": "max_tokens", "value": 2048},
                    {"key": "deepseek_api_key", "value": "secret-token"},
                ]
            },
        )
        self.assertEqual(patch_response.status_code, 200)

        patched_items = patch_response.json()["data"]["items"]
        patched_base_url = next(
            item for item in patched_items if item["key"] == "deepseek_base_url"
        )
        self.assertEqual(patched_base_url["value"], "https://custom.example.com")

        patched_tokens = next(
            item for item in patched_items if item["key"] == "max_tokens"
        )
        self.assertEqual(patched_tokens["value"], 2048)

        patched_sensitive = next(
            item for item in patched_items if item["key"] == "deepseek_api_key"
        )
        self.assertEqual(patched_sensitive["value"], None)
        self.assertEqual(patched_sensitive["has_value"], True)

    def test_not_found_resources_return_404(self):
        """不存在的资源应返回 404。"""
        self.assertEqual(self.request("GET", "/api/courses/99999").status_code, 404)
        self.assertEqual(self.request("GET", "/api/sessions/99999").status_code, 404)
        self.assertEqual(self.request("GET", "/api/questions/99999").status_code, 404)


def main():
    """运行 API 测试。"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAPI)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
