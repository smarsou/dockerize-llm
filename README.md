# DockerizeLLM

DockerizeLLM is a Python script designed to make serving large language models (LLMs) simple. It automates the process of finding, downloading, and serving models from the Hugging Face Hub using `llama.cpp` as the backend. The resulting system runs as a Docker container with an OpenAI-compatible API.

## Features

- Search for gguf models on the Hugging Face Hub.
- Download the selected model files.
- Serve the model with `llama.cpp`.
- Expose the model using an OpenAI-compatible API (`llama-cpp-python[server]`).
- Dockerize the entire setup for deployment.

## Version

**Current version:** `1.0`

## Configuration

- **Backend**: `llama.cpp` (built from source)
- **API**: Built-in `llama.cpp` API via the Python module `llama-cpp-python[server]`.

## How It Works

1. Search for models on Hugging Face by keywords and tags.
2. Download the required gguf files from the repository.
3. Build a Docker image containing:
   - `llama.cpp` compiled from source.
   - The selected gguf model file.
   - The API for serving the model.
4. Serve the model as an OpenAI-compatible API endpoint.

## Prerequisites

- Docker and Docker Daemon installed on your system.
- Python 3.8+ with `pip` for managing dependencies.

## How to Use

### Arguments

The script accepts the following arguments:

- `image_name` (str): Name for the Docker image.
- `image_tag` (str): Tag for the Docker image.
- `build_type` (str, optional): Build type for `llama.cpp` (e.g., `openblas`, `None`).

### Running the Script

1. Clone this repository.
2. Install required Python packages:
   ```bash
   pip install -r requirements.txt

### Run the built image

Run a container with the following command :

    docker run -dit -p 2600:2600 <docker_image_name>:<docker_image_tag>

Then your model is served into this container and is accessible through a OpenAI compatible API.

### Example for testing

    1. Retrieve the id of the model with the following command:
    curl http://localhost:2600/v1/models -H 'Content-Type: application/json'

    2. Send a chat completion request to the served model using the following command:
    curl http://localhost:2600/v1/chat/completions -H 'Content-Type: application/json' -d '{"model": "<model_id_found_with_the_previous_command>", "messages": [{"role": "user", "content": "Are you loaded ?"}], "temperature": 0.9, "max_tokens":25}'

