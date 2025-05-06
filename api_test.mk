# API测试相关命令
# 设置API基础URL
API_URL ?= http://localhost:8000

# 测试样例音频文件路径
SAMPLE_AUDIO ?= sample.mp3

# 测试健康检查接口
test-health:
	@echo "测试API健康状态..."
	@curl -s $(API_URL)/ | grep message || echo "健康检查失败"

# 测试获取模型列表
test-models:
	@echo "获取可用模型列表..."
	@curl -s $(API_URL)/models

# 测试转录功能 (需要有测试音频文件)
test-transcribe:
	@if [ ! -f $(SAMPLE_AUDIO) ]; then \
		echo "错误: 测试音频文件 $(SAMPLE_AUDIO) 不存在"; \
		echo "请设置正确的音频文件路径: make test-transcribe SAMPLE_AUDIO=./data/sample.flac"; \
		exit 1; \
	fi
	@echo "测试音频转录功能..."
	curl -s -X POST \
		$(API_URL)/transcribe \
		-H "accept: application/json" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(SAMPLE_AUDIO)" \
		-F "model=turbo" \
		-F "return_segments=true"

# 测试带语言参数的转录
test-transcribe-lang:
	@if [ ! -f $(SAMPLE_AUDIO) ]; then \
		echo "错误: 测试音频文件 $(SAMPLE_AUDIO) 不存在"; \
		echo "请设置正确的音频文件路径: make test-transcribe-lang SAMPLE_AUDIO=./data/sample.flac LANG=zh"; \
		exit 1; \
	fi
	@echo "测试指定语言的音频转录功能..."
	@curl -s -X POST \
		$(API_URL)/transcribe \
		-H "accept: application/json" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(SAMPLE_AUDIO)" \
		-F "model=turbo" \
		-F "language=$(LANG)" \
		-F "return_segments=true"

# 测试翻译功能
test-translate:
	@if [ ! -f $(SAMPLE_AUDIO) ]; then \
		echo "错误: 测试音频文件 $(SAMPLE_AUDIO) 不存在"; \
		echo "请设置正确的音频文件路径: make test-translate SAMPLE_AUDIO=./data/"; \
		exit 1; \
	fi
	@echo "测试音频翻译功能..."
	@curl -s -X POST \
		$(API_URL)/transcribe \
		-H "accept: application/json" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(SAMPLE_AUDIO)" \
		-F "model=turbo" \
		-F "task=translate" \
		-F "return_segments=true"

# 下载样例音频用于测试
download-sample:
	@echo "下载样例音频文件..."
	@if [ ! -f sample.mp3 ]; then \
		curl -L "https://github.com/openai/whisper/raw/main/tests/jfk.flac" -o data/sample.flac; \
		echo "样例音频已下载为 sample.flac"; \
	else \
		echo "样例音频文件已存在"; \
	fi

# 运行所有API测试
test-all: test-health test-models download-sample test-transcribe

# 定义这个Makefile片段中的伪目标
.PHONY: test-health test-models test-transcribe test-transcribe-lang test-translate download-sample test-all 