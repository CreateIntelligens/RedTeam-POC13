#!/bin/bash
set -e

# Initialize conda for bash shell
eval "$(conda shell.bash hook)"

# Activate amlenv environment (Python 3.12)
conda activate amlenv
echo "✅ Activated conda environment: amlenv (Python 3.12)"

# Set PYTHONPATH to prioritize local PyRIT code
export PYTHONPATH="/workspace/pyrit:$PYTHONPATH"
echo "✅ Set PYTHONPATH to use local PyRIT development version"

# PyRIT is already mounted, no need to clone
echo "PyRIT project mounted at /workspace/pyrit"

# Copy doc folder if CLONE_DOCS is enabled
if [ "$CLONE_DOCS" = "true" ] && [ -d "/workspace/pyrit/doc" ]; then
    echo "Copying documentation..."
    mkdir -p /workspace/notebooks
    cp -r /workspace/pyrit/doc/* /workspace/notebooks/
fi

# Default to CPU mode
export CUDA_VISIBLE_DEVICES="-1"

# Only try to use GPU if explicitly enabled
if [ "$ENABLE_GPU" = "true" ] && command -v nvidia-smi &> /dev/null; then
    echo "GPU detected and explicitly enabled, running with GPU support"
    export CUDA_VISIBLE_DEVICES="0"
else
    echo "Running in CPU-only mode"
    export CUDA_VISIBLE_DEVICES="-1"
fi

# Print PyRIT version
python -c "import pyrit; print(f'Running PyRIT version: {pyrit.__version__}')"

# Start PyRIT Frontend in background
if [ -d "/workspace/pyrit/pyrit_frontend" ]; then
    echo "🚀 啟動 PyRIT Frontend (端口 8889)..."
    cd /workspace/pyrit/pyrit_frontend
    nohup python main.py > /tmp/frontend.log 2>&1 &
    echo "✅ PyRIT Frontend 已在背景啟動"
    echo "🌐 訪問界面: http://localhost:8889"
    echo "📡 API 文檔: http://localhost:8889/docs"
else
    echo "⚠️  PyRIT Frontend 目錄不存在"
fi

# Execute the command passed to docker run (or the CMD if none provided)
exec "$@"
