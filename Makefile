.PHONY: help setup venv install run dev clean docker-build docker-run docker-up test-health test-models test-transcribe test-transcribe-lang test-translate download-sample test-all

# 引入API测试相关的规则
include api_test.mk

# 默认目标，显示帮助信息
help:
	@echo "可用命令:"
	@echo "  make help         - 显示帮助信息"
	@echo "  make setup        - 创建虚拟环境并安装依赖"
	@echo "  make venv         - 仅创建虚拟环境"
	@echo "  make install      - 安装依赖"
	@echo "  make run          - 运行API服务"
	@echo "  make dev          - 以开发模式运行API服务(支持热重载)"
	@echo "  make clean        - 清理临时文件和缓存"
	@echo "  make docker-build - 构建Docker镜像"
	@echo "  make docker-run   - 运行Docker容器"
	@echo "  make docker-up    - 使用docker-compose启动服务"
	@echo ""
	@echo "API测试命令:"
	@echo "  make test-health  - 测试API健康状态"
	@echo "  make test-models  - 获取可用模型列表"
	@echo "  make download-sample - 下载样例音频用于测试"
	@echo "  make test-transcribe - 测试音频转录功能"
	@echo "  make test-transcribe-lang LANG=zh - 测试指定语言的转录"
	@echo "  make test-translate - 测试音频翻译功能"
	@echo "  make test-all     - 运行所有API测试"

# 完整设置
setup: venv install

# 创建虚拟环境
venv:
	python -m venv .venv
	@echo "虚拟环境已创建，请激活:"
	@echo "  source .venv/bin/activate  # Linux/Mac"
	@echo "  .venv\\Scripts\\activate    # Windows"

# 安装依赖
install:
	pip install -r requirements.txt

# 运行服务
run:
	python main.py

# 开发模式运行(支持热重载)
dev:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 清理临时文件和缓存
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .coverage -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

# Docker操作
docker-build:
	docker build -t voxscribe-api .

docker-run: docker-build
	docker run -p 8000:8000 voxscribe-api

docker-up:
	docker-compose up --build 