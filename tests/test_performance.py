"""
性能测试用例 - v9.0.0.9 测试验证

测试目标:
1. API 响应时间测试
2. SSE 消息延迟测试
3. 大消息量处理测试
"""

import asyncio
import json
import time
import pytest
import httpx
from typing import List, Dict, Any


# 测试服务器配置
BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 300.0  # 5分钟超时


class PerformanceMetrics:
    """性能指标收集器"""
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def add_result(self, test_name: str, duration_ms: float, details: Dict[str, Any] = None):
        self.results.append({
            "test_name": test_name,
            "duration_ms": duration_ms,
            "details": details or {},
            "timestamp": time.time()
        })

    def print_summary(self):
        print("\n" + "=" * 60)
        print("性能测试结果汇总")
        print("=" * 60)
        for r in self.results:
            print(f"\n测试: {r['test_name']}")
            print(f"  耗时: {r['duration_ms']:.2f} ms")
            if r['details']:
                for k, v in r['details'].items():
                    print(f"  {k}: {v}")
        print("\n" + "=" * 60)


metrics = PerformanceMetrics()


@pytest.fixture
def client():
    """创建 HTTP 客户端"""
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


@pytest.fixture
async def async_client():
    """创建异步 HTTP 客户端"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


class TestAPIResponseTime:
    """API 响应时间测试"""

    def test_index_page_load_time(self, client):
        """测试首页加载响应时间"""
        start_time = time.time()
        response = client.get("/")
        duration_ms = (time.time() - start_time) * 1000

        metrics.add_result("首页加载", duration_ms, {
            "status_code": response.status_code,
            "content_length": len(response.content)
        })

        assert response.status_code == 200
        print(f"\n首页加载时间: {duration_ms:.2f} ms")

    def test_static_file_load_time(self, client):
        """测试静态文件加载时间"""
        # 测试 JavaScript 文件
        start_time = time.time()
        response = client.get("/static/app.js")
        js_duration_ms = (time.time() - start_time) * 1000

        metrics.add_result("JavaScript文件加载", js_duration_ms, {
            "status_code": response.status_code,
            "content_length": len(response.content)
        })

        assert response.status_code == 200

        # 测试 CSS 文件
        start_time = time.time()
        response = client.get("/static/css/layout.css")
        css_duration_ms = (time.time() - start_time) * 1000

        metrics.add_result("CSS文件加载", css_duration_ms, {
            "status_code": response.status_code,
            "content_length": len(response.content)
        })

        assert response.status_code == 200

        print(f"\nJavaScript 加载时间: {js_duration_ms:.2f} ms")
        print(f"CSS 加载时间: {css_duration_ms:.2f} ms")

    def test_api_health_check(self, client):
        """测试健康检查端点响应时间"""
        start_time = time.time()
        response = client.get("/api/status")
        duration_ms = (time.time() - start_time) * 1000

        metrics.add_result("健康检查API", duration_ms, {
            "status_code": response.status_code
        })

        assert response.status_code == 200
        print(f"\n健康检查响应时间: {duration_ms:.2f} ms")

    @pytest.mark.asyncio
    async def test_task_api_response_time(self, async_client):
        """测试任务执行 API 响应时间（简单任务）"""
        # 使用一个非常简单的任务来测试 API 响应时间
        payload = {
            "prompt": "你好",
            "working_dir": ".",
        }

        start_time = time.time()
        try:
            response = await async_client.post("/api/task", json=payload)
            duration_ms = (time.time() - start_time) * 1000
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            metrics.add_result("任务API响应时间", duration_ms, {
                "error": str(e)
            })
            pytest.skip(f"任务API测试跳过: {e}")
            return

        metrics.add_result("任务API响应时间", duration_ms, {
            "status_code": response.status_code
        })

        print(f"\n任务API响应时间: {duration_ms:.2f} ms")


class TestSSEMessageLatency:
    """SSE 消息延迟测试"""

    @pytest.mark.asyncio
    async def test_sse_connection_time(self, async_client):
        """测试 SSE 连接建立时间"""
        payload = {
            "prompt": "说一个字",
            "working_dir": ".",
            "new_session": True
        }

        start_time = time.time()
        first_message_time = None
        message_count = 0

        try:
            async with async_client.stream("POST", "/api/task/stream", json=payload) as response:
                # 计算连接建立时间
                connect_time = (time.time() - start_time) * 1000

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        current_time = time.time()
                        if first_message_time is None:
                            first_message_time = (current_time - start_time) * 1000
                        message_count += 1

                        # 尝试解析消息
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "complete" or data.get("type") == "error":
                                break
                        except:
                            pass

                total_time = (time.time() - start_time) * 1000
        except Exception as e:
            metrics.add_result("SSE连接测试", 0, {
                "error": str(e)
            })
            pytest.skip(f"SSE测试跳过: {e}")
            return

        metrics.add_result("SSE连接建立", connect_time, {
            "message_count": message_count
        })
        metrics.add_result("SSE首条消息延迟", first_message_time or 0, {
            "message_count": message_count
        })
        metrics.add_result("SSE总执行时间", total_time, {
            "message_count": message_count
        })

        print(f"\nSSE 连接建立时间: {connect_time:.2f} ms")
        print(f"SSE 首条消息延迟: {first_message_time:.2f} ms")
        print(f"SSE 消息数量: {message_count}")
        print(f"SSE 总执行时间: {total_time:.2f} ms")

    @pytest.mark.asyncio
    async def test_sse_message_intervals(self, async_client):
        """测试 SSE 消息间隔时间"""
        payload = {
            "prompt": "列出当前目录的文件",
            "working_dir": ".",
            "new_session": True
        }

        message_times: List[float] = []
        start_time = time.time()

        try:
            async with async_client.stream("POST", "/api/task/stream", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        current_time = time.time()
                        message_times.append(current_time - start_time)

                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "complete" or data.get("type") == "error":
                                break
                        except:
                            pass
        except Exception as e:
            pytest.skip(f"SSE消息间隔测试跳过: {e}")
            return

        # 计算消息间隔
        intervals = []
        for i in range(1, len(message_times)):
            interval = (message_times[i] - message_times[i-1]) * 1000
            intervals.append(interval)

        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            max_interval = max(intervals)
            min_interval = min(intervals)

            metrics.add_result("SSE消息间隔", avg_interval, {
                "avg_interval_ms": avg_interval,
                "max_interval_ms": max_interval,
                "min_interval_ms": min_interval,
                "message_count": len(message_times)
            })

            print(f"\nSSE 消息间隔统计:")
            print(f"  平均: {avg_interval:.2f} ms")
            print(f"  最大: {max_interval:.2f} ms")
            print(f"  最小: {min_interval:.2f} ms")


class TestLargeMessageHandling:
    """大消息量处理测试"""

    @pytest.mark.asyncio
    async def test_large_prompt_handling(self, async_client):
        """测试大 prompt 处理能力"""
        # 创建一个大的 prompt (约 10KB)
        large_prompt = "测试 " * 1000  # 约 8KB

        payload = {
            "prompt": large_prompt,
            "working_dir": ".",
            "new_session": True
        }

        start_time = time.time()

        try:
            async with async_client.stream("POST", "/api/task/stream", json=payload) as response:
                message_count = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        message_count += 1
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "complete" or data.get("type") == "error":
                                break
                        except:
                            pass
        except Exception as e:
            metrics.add_result("大Prompt处理", 0, {
                "error": str(e)
            })
            pytest.skip(f"大Prompt测试跳过: {e}")
            return

        duration_ms = (time.time() - start_time) * 1000

        metrics.add_result("大Prompt处理", duration_ms, {
            "prompt_size_kb": len(large_prompt) / 1024,
            "message_count": message_count
        })

        print(f"\n大Prompt处理:")
        print(f"  Prompt大小: {len(large_prompt)/1024:.2f} KB")
        print(f"  处理时间: {duration_ms:.2f} ms")
        print(f"  消息数量: {message_count}")

    @pytest.mark.asyncio
    async def test_high_message_volume(self, async_client):
        """测试高消息量处理能力"""
        # 发送一个会产生多轮工具调用的任务
        payload = {
            "prompt": "查看当前目录结构，列出所有文件",
            "working_dir": ".",
            "new_session": True
        }

        start_time = time.time()
        message_count = 0
        total_content_length = 0

        try:
            async with async_client.stream("POST", "/api/task/stream", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        message_count += 1
                        try:
                            data = json.loads(line[6:])
                            if data.get("content"):
                                total_content_length += len(data.get("content", ""))
                            if data.get("type") == "complete" or data.get("type") == "error":
                                break
                        except:
                            pass
        except Exception as e:
            metrics.add_result("高消息量处理", 0, {
                "error": str(e)
            })
            pytest.skip(f"高消息量测试跳过: {e}")
            return

        duration_ms = (time.time() - start_time) * 1000

        metrics.add_result("高消息量处理", duration_ms, {
            "message_count": message_count,
            "total_content_length": total_content_length,
            "throughput_msg_per_sec": (message_count / duration_ms * 1000) if duration_ms > 0 else 0
        })

        print(f"\n高消息量处理:")
        print(f"  消息数量: {message_count}")
        print(f"  总内容长度: {total_content_length} 字符")
        print(f"  处理时间: {duration_ms:.2f} ms")
        print(f"  吞吐量: {message_count / duration_ms * 1000:.2f} 消息/秒")


class TestConcurrentRequests:
    """并发请求测试"""

    @pytest.mark.asyncio
    async def test_concurrent_task_requests(self, async_client):
        """测试并发任务请求"""

        async def run_single_task(task_id: int):
            payload = {
                "prompt": f"测试任务 {task_id}: 你好",
                "working_dir": ".",
                "new_session": True
            }
            start_time = time.time()
            try:
                async with async_client.stream("POST", "/api/task/stream", json=payload) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if data.get("type") == "complete" or data.get("type") == "error":
                                    break
                            except:
                                pass
                return time.time() - start_time
            except Exception as e:
                return None

        # 并发执行 2 个任务
        start_time = time.time()
        results = await asyncio.gather(
            run_single_task(1),
            run_single_task(2),
        )
        total_time = time.time() - start_time

        valid_results = [r for r in results if r is not None]
        if valid_results:
            avg_time = sum(valid_results) / len(valid_results)

            metrics.add_result("并发任务处理", total_time * 1000, {
                "task_count": len(valid_results),
                "avg_task_time_ms": avg_time * 1000,
                "total_time_ms": total_time * 1000
            })

            print(f"\n并发任务处理:")
            print(f"  任务数量: {len(valid_results)}")
            print(f"  平均任务时间: {avg_time * 1000:.2f} ms")
            print(f"  总执行时间: {total_time * 1000:.2f} ms")


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时的钩子"""
    metrics.print_summary()
