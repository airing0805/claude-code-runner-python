"""
手动性能测试脚本

用于在服务器运行时执行快速性能测试
"""
import httpx
import time
import json
import asyncio
from typing import List, Dict, Any

BASE_URL = 'http://127.0.0.1:8000'


def test_api_response_time():
    """测试 API 响应时间"""
    print('=' * 60)
    print('API 响应时间测试')
    print('=' * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    results = []

    # 测试首页加载
    start = time.time()
    r = client.get('/')
    duration_ms = (time.time() - start) * 1000
    results.append(('首页加载', duration_ms, r.status_code == 200))
    print(f'\n1. 首页加载时间: {duration_ms:.2f} ms (status: {r.status_code})')

    # 测试静态文件
    start = time.time()
    r = client.get('/static/app.js')
    js_time = (time.time() - start) * 1000
    results.append(('JS文件加载', js_time, r.status_code == 200))
    print(f'2. JS文件加载时间: {js_time:.2f} ms (status: {r.status_code})')

    start = time.time()
    r = client.get('/static/css/layout.css')
    css_time = (time.time() - start) * 1000
    results.append(('CSS文件加载', css_time, r.status_code == 200))
    print(f'3. CSS文件加载时间: {css_time:.2f} ms (status: {r.status_code})')

    # 测试健康检查
    start = time.time()
    r = client.get('/api/status')
    status_time = (time.time() - start) * 1000
    results.append(('健康检查API', status_time, r.status_code == 200))
    print(f'4. 健康检查API: {status_time:.2f} ms (status: {r.status_code})')

    # 测试会话列表API
    start = time.time()
    r = client.get('/api/sessions')
    session_time = (time.time() - start) * 1000
    results.append(('会话列表API', session_time, r.status_code == 200))
    print(f'5. 会话列表API: {session_time:.2f} ms (status: {r.status_code})')

    return results


async def test_sse_latency():
    """测试 SSE 消息延迟"""
    print('\n' + '=' * 60)
    print('SSE 消息延迟测试')
    print('=' * 60)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        payload = {
            "prompt": "说一个词: hello",
            "working_dir": ".",
            "new_session": True
        }

        start_time = time.time()
        first_message_time = None
        message_count = 0

        try:
            async with client.stream("POST", "/api/task/stream", json=payload) as response:
                connect_time = (time.time() - start_time) * 1000
                print(f'\nSSE 连接建立时间: {connect_time:.2f} ms')

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        current_time = time.time()
                        if first_message_time is None:
                            first_message_time = (current_time - start_time) * 1000
                        message_count += 1

                        try:
                            data = json.loads(line[6:])
                            msg_type = data.get("type")
                            print(f'  消息 #{message_count}: {msg_type}')
                            if msg_type in ("complete", "error"):
                                break
                        except:
                            pass

                total_time = (time.time() - start_time) * 1000
                print(f'\n首条消息延迟: {first_message_time:.2f} ms')
                print(f'消息总数: {message_count}')
                print(f'总执行时间: {total_time:.2f} ms')

                return {
                    'connect_time': connect_time,
                    'first_message_time': first_message_time,
                    'message_count': message_count,
                    'total_time': total_time
                }
        except Exception as e:
            print(f'\nSSE 测试失败: {e}')
            return None


async def test_large_message():
    """测试大消息量处理"""
    print('\n' + '=' * 60)
    print('大消息量处理测试')
    print('=' * 60)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        # 大 prompt 测试
        large_prompt = "测试 " * 1000

        payload = {
            "prompt": large_prompt,
            "working_dir": ".",
            "new_session": True
        }

        start_time = time.time()
        message_count = 0

        try:
            async with client.stream("POST", "/api/task/stream", json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        message_count += 1
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") in ("complete", "error"):
                                break
                        except:
                            pass

            duration_ms = (time.time() - start_time) * 1000

            print(f'\n大Prompt处理测试:')
            print(f'  Prompt大小: {len(large_prompt) / 1024:.2f} KB')
            print(f'  处理时间: {duration_ms:.2f} ms')
            print(f'  消息数量: {message_count}')

            return {
                'prompt_size_kb': len(large_prompt) / 1024,
                'duration_ms': duration_ms,
                'message_count': message_count
            }
        except Exception as e:
            print(f'\n大消息量测试失败: {e}')
            return None


async def main():
    """主函数"""
    print('\n' + '=' * 60)
    print('Claude Code Runner 性能测试')
    print('测试时间:', time.strftime('%Y-%m-%d %H:%M:%S'))
    print('=' * 60)

    # API 响应时间测试
    api_results = test_api_response_time()

    # SSE 延迟测试
    sse_result = await test_sse_latency()

    # 大消息量测试
    large_msg_result = await test_large_message()

    # 总结
    print('\n' + '=' * 60)
    print('测试结果总结')
    print('=' * 60)

    print('\n[API 响应时间]')
    for name, duration, success in api_results:
        status = 'PASS' if success else 'FAIL'
        print(f'  {name}: {duration:.2f} ms [{status}]')

    if sse_result:
        print('\n[SSE 消息延迟]')
        print(f'  连接建立: {sse_result["connect_time"]:.2f} ms')
        print(f'  首条消息: {sse_result["first_message_time"]:.2f} ms')
        print(f'  总执行时间: {sse_result["total_time"]:.2f} ms')

    if large_msg_result:
        print('\n[大消息量处理]')
        print(f'  Prompt大小: {large_msg_result["prompt_size_kb"]:.2f} KB')
        print(f'  处理时间: {large_msg_result["duration_ms"]:.2f} ms')
        print(f'  消息数量: {large_msg_result["message_count"]}')

    print('\n' + '=' * 60)
    print('测试完成')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(main())
