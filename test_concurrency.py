#!/usr/bin/env python3
"""
并发测试脚本 - 用于测试VoxScribe API的并发处理能力
"""

import asyncio
import aiohttp
import time
import os
from pathlib import Path
import argparse


async def upload_audio_file(session, url, file_path, model="tiny", token=None):
    """上传音频文件并获取转录结果"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    data = aiohttp.FormData()
    data.add_field('file', open(file_path, 'rb'), filename=os.path.basename(file_path))
    data.add_field('model', model)
    data.add_field('return_segments', 'false')
    
    start_time = time.time()
    try:
        async with session.post(f"{url}/transcribe", data=data, headers=headers) as response:
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status == 200:
                result = await response.json()
                return {
                    "success": True,
                    "duration": duration,
                    "text_length": len(result.get("text", "")),
                    "language": result.get("language", "unknown")
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "duration": duration,
                    "error": f"HTTP {response.status}: {error_text}"
                }
    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "duration": end_time - start_time,
            "error": str(e)
        }


async def test_concurrent_requests(url, file_path, num_requests=5, model="tiny", token=None):
    """测试并发请求"""
    print(f"开始并发测试：{num_requests} 个并发请求")
    print(f"API URL: {url}")
    print(f"音频文件: {file_path}")
    print(f"使用模型: {model}")
    print("-" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 创建并发任务
        tasks = []
        for i in range(num_requests):
            task = upload_audio_file(session, url, file_path, model, token)
            tasks.append(task)
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 记录结束时间
        end_time = time.time()
        total_duration = end_time - start_time
        
        # 分析结果
        successful_requests = 0
        failed_requests = 0
        total_processing_time = 0
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_requests += 1
                errors.append(f"请求 {i+1}: {str(result)}")
            elif result["success"]:
                successful_requests += 1
                total_processing_time += result["duration"]
                print(f"请求 {i+1}: 成功 - {result['duration']:.2f}s - 语言: {result['language']} - 文本长度: {result['text_length']}")
            else:
                failed_requests += 1
                errors.append(f"请求 {i+1}: {result['error']}")
                print(f"请求 {i+1}: 失败 - {result['error']}")
        
        # 打印统计信息
        print("-" * 60)
        print(f"并发测试结果:")
        print(f"总请求数: {num_requests}")
        print(f"成功请求: {successful_requests}")
        print(f"失败请求: {failed_requests}")
        print(f"总耗时: {total_duration:.2f} 秒")
        
        if successful_requests > 0:
            avg_processing_time = total_processing_time / successful_requests
            print(f"平均处理时间: {avg_processing_time:.2f} 秒")
            print(f"并发效率: {(total_processing_time / total_duration):.2f}x")
            print(f"吞吐量: {successful_requests / total_duration:.2f} 请求/秒")
        
        if errors:
            print("\n错误详情:")
            for error in errors:
                print(f"  {error}")
        
        return {
            "total_requests": num_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "total_duration": total_duration,
            "average_processing_time": total_processing_time / successful_requests if successful_requests > 0 else 0,
            "throughput": successful_requests / total_duration
        }


async def test_health_check(url):
    """测试健康检查端点"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health") as response:
                if response.status == 200:
                    result = await response.json()
                    print("API 健康状态:")
                    print(f"  状态: {result.get('status', 'unknown')}")
                    print(f"  已加载模型: {result.get('loaded_models', [])}")
                    print(f"  工作线程数: {result.get('worker_threads', 'unknown')}")
                    print(f"  设备: {result.get('device', 'unknown')}")
                    return True
                else:
                    print(f"健康检查失败: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"健康检查错误: {str(e)}")
        return False


def find_audio_file():
    """查找测试音频文件"""
    # 常见的测试音频文件路径
    possible_paths = [
        "sample.mp3",
        "test.wav",
        "audio.m4a",
        "test_audio.flac",
        "data/sample.mp3",
        "test_data/audio.wav"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="VoxScribe API 并发测试")
    parser.add_argument("--url", default="http://localhost:8000", help="API基础URL")
    parser.add_argument("--file", help="测试音频文件路径")
    parser.add_argument("--requests", type=int, default=5, help="并发请求数量")
    parser.add_argument("--model", default="tiny", help="使用的Whisper模型")
    parser.add_argument("--token", help="API认证令牌")
    
    args = parser.parse_args()
    
    # 查找音频文件
    audio_file = args.file or find_audio_file()
    if not audio_file:
        print("错误: 找不到测试音频文件")
        print("请使用 --file 参数指定音频文件路径")
        print("或在当前目录放置名为 sample.mp3, test.wav 等的音频文件")
        return
    
    if not os.path.exists(audio_file):
        print(f"错误: 音频文件不存在: {audio_file}")
        return
    
    print("VoxScribe API 并发性能测试")
    print("=" * 60)
    
    # 健康检查
    print("1. 执行健康检查...")
    if not await test_health_check(args.url):
        print("健康检查失败，请确保API服务正在运行")
        return
    
    print("\n" + "=" * 60)
    
    # 并发测试
    print("2. 执行并发测试...")
    results = await test_concurrent_requests(
        args.url, 
        audio_file, 
        args.requests, 
        args.model,
        args.token
    )
    
    print("\n" + "=" * 60)
    print("测试完成！")
    
    # 性能评估
    if results["successful_requests"] > 0:
        if results["throughput"] > 1.0:
            print("✅ 优秀的并发性能")
        elif results["throughput"] > 0.5:
            print("✅ 良好的并发性能")
        else:
            print("⚠️  并发性能有待提升")
    else:
        print("❌ 所有请求都失败了")


if __name__ == "__main__":
    asyncio.run(main()) 