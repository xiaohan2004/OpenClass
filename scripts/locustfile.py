from locust import HttpUser, task, between

class ApiPerformanceUser(HttpUser):
    wait_time = between(1, 2)

    host = "http://127.0.0.1:8000"

    # ===== 1. 查询课程详情 =====
    @task(3)
    def get_course(self):
        course_id = 1  # 可以换成多个id做随机
        self.client.get(f"/api/courses/{course_id}")

    # ===== 2. 查询日志列表（分页 + filter）=====
    @task(2)
    def list_relay_logs(self):
        self.client.get("/api/relay-logs?limit=20&offset=0")

    # ===== 3. 带过滤条件查询 =====
    @task(1)
    def list_relay_logs_filtered(self):
        self.client.get("/api/relay-logs?service_type=LLM&limit=20&offset=0")

    # ===== 4. 查询单条日志详情 =====
    @task(2)
    def get_relay_log_by_id(self):
        log_id = 1
        self.client.get(f"/api/relay-logs/{log_id}")