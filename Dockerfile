
# Use an official Ubuntu as a parent image
FROM debian:bookworm

# Update apt package index and install necessary packages
RUN apt-get update && apt-get install -y     git     make     build-essential     ccache     python3     python3-pip

# Change working directory to /root/
WORKDIR /root/

# Clone the llama.cpp repository
RUN git clone https://github.com/ggerganov/llama.cpp

# Change working directory to /root/llama.cpp
WORKDIR /root/llama.cpp

# Install Python requirements
RUN pip install -r requirements.txt --break-system-packages

# Build llama.cpp with debug flag
RUN make LLAMA_DEBUG=1 

# Copy the GGUF model from the host into the container
COPY gpt2.Q6_K.gguf /root/llama.cpp/

# Install llama-cpp-python[server]
RUN pip install 'llama-cpp-python[server]' --break-system-packages

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=2600

# Expose port 2600
EXPOSE 2600

# Start llama_cpp server
CMD ["python3", "-m", "llama_cpp.server", "--model=gpt2.Q6_K.gguf"]
