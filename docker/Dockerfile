# Base image from Microsoft Azure with Python 3.12
FROM mcr.microsoft.com/azureml/minimal-py312-inference:20250310.v1
LABEL description="Docker container for PyRIT with Jupyter Notebook integration"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Switch to root user to install packages
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    build-essential \
    ca-certificates \
    unixodbc \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /workspace/pyrit

# Copy requirements file
COPY requirements.txt /workspace/requirements.txt

# Install torch, torchvision, torchaudio from PyTorch with CUDA 11.8 support
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu118 torch==2.6.0+cu118 torchvision==0.21.0+cu118 torchaudio==2.6.0+cu118
# Install all Python dependencies at once with pinned versions
RUN pip install --no-cache-dir -r /workspace/requirements.txt

# Install PyRIT from PyPI (the official way)
RUN pip install --no-cache-dir pyrit[dev,all]


# Create directories
RUN mkdir -p /workspace/pyrit && \
    chmod -R 777 /workspace

# Check PyRIT version
RUN python -c "import pyrit; print(f'PyRIT version: {pyrit.__version__}')"

RUN chown -R dockeruser:dockeruser /workspace

# Create and set permissions for the startup script
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

# Switch to non-root user
USER dockeruser

# Initialize conda and activate amlenv by default for interactive shells
RUN echo 'eval "$(conda shell.bash hook)"' >> ~/.bashrc && \
    echo 'conda activate amlenv' >> ~/.bashrc && \
    echo 'echo "✅ Auto-activated conda environment: amlenv (Python 3.12)"' >> ~/.bashrc

# Set environment variable to always use amlenv python
ENV PATH="/opt/miniconda/envs/amlenv/bin:$PATH"

# Expose port for JupyterLab and PyRIT Frontend
EXPOSE 8888 8889

# Set the entrypoint to the startup script and default command to launch JupyterLab
ENTRYPOINT ["/workspace/start.sh"]
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''", "--notebook-dir=/workspace"]
