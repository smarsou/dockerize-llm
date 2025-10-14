#!/usr/bin/env python3
"""
This python module meet the following requirements :
-> Check HuggingFace for gguf models and download them.
-> Serve the model with llama.cpp 
-> Serve the model with an OpenAI endpoint API.
-> Dockerize the whole 

# VERSION

VERSION : 1.0

# CONFIG

BACKEND : llama.cpp from source
API : Built-in llama.cpp API (python module "llama-cpp-python[server]")

"""


#----------------------
# Dependencies
#----------------------

import logging, re, requests, argparse, sys
from huggingface_hub import login
from huggingface_hub import get_hf_file_metadata, hf_hub_url, repo_info, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError, RevisionNotFoundError
from typing import Optional
from huggingface_hub import snapshot_download

#----------------------
# CONFIG
#----------------------

logging.basicConfig(level=logging.INFO)

GO_URL = "https://go.dev/dl/go1.21.1.linux-amd64.tar.gz"

#----------------------
# FUNCTIONS
#----------------------

def get_parser():
    parser = argparse.ArgumentParser(
                    prog='DockerizeLLM',
                    description='It suggest you to choose an LLM from the HunggingFace Hub and then build an image to serve it using llama.cpp')
    parser.add_argument('--image_name', type=str, required=True, help="name to use for the docker image which will be built.")
    parser.add_argument('--image_tag', type=str, required=True, help="tag to use for the docker image which will be built.")
    parser.add_argument('--build_type', type=str, default=None, help="""parameter used by llama.cpp for when building the repository, possible values : [None, "openblas", (soon: "clblast", "cuda")]""")
    parser.add_argument('--embeddings', action='store_true', help="""If set, the model will be used for embeddings. Note that not all models support this feature.""")
    return parser

#----------------------
# CLASSES
#----------------------

class HuggingFaceInterface():
    """
    Provides methods for interacting with the Hugging Face API,
    including searching for models, looking for gguf files in repositories,
    and downloading model files.
    """
    
    def __init__(self, authenticate = False) -> None:
        if authenticate:
            login()

    def repo_exists(self, repo_id: str, repo_type: Optional[str] = None, token: Optional[str] = None) -> bool:
        """
        Checks if a repository exists.

        Returns:
            bool: True if the repository exists, False otherwise. 
                Note that False may also be returned if you lack permissions to access the repository. 
                Ensure you are authenticated and have the necessary permissions.
        Credits:
        https://github.com/huggingface/huggingface_hub/issues/36#issuecomment-1619942423
        """
        
        try:
            res = repo_info(repo_id, repo_type=repo_type, token=token)
            return True
        except RepositoryNotFoundError:
            return False

    def file_exists(
        self,
        repo_id: str,
        filename: str,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        token: Optional[str] = None,
    ) -> bool:
        """
        Check if a file exists in a given repository.
        
        Returns:
            bool: True if the repository exists, False otherwise. 
                Note that False may also be returned if you lack permissions to access the repository. 
                Ensure you are authenticated and have the necessary permissions.
        Credits:
        https://github.com/huggingface/huggingface_hub/issues/36#issuecomment-1619942423
        """
        url = hf_hub_url(repo_id=repo_id, repo_type=repo_type, revision=revision, filename=filename)
        try:
            get_hf_file_metadata(url, token=token)
            return True
        except (RepositoryNotFoundError, EntryNotFoundError, RevisionNotFoundError):
            return False

    def search_repo_in_hub(self, text, tag=""):
        """
        Given a string ("text"), search through all the HF Hub for the models which the id match the string.
        """
        
        url = f'https://huggingface.co/api/models?search={text}'
        res = requests.get(url, timeout=10)
        for model in res.json():
            if not tag:
                print("->",model['id'])
            else:
                for t in model['tags']:
                    if t == tag:
                        print("->",model['id'])
                        break

    def list_gguf_files_in_repo(self,repo_id):
        """"
        List all the gguf files in a given HuggingFace repository.
        """
        for file in repo_info(repo_id).siblings:
            if re.match("^.*.gguf$",file.rfilename):
                print("->",file.rfilename)

    def download_file(self,repo_id, filename, output_dir="."):
        """
        Download a file from a given HuggingFace repository.
        """
        hf_hub_download(repo_id=repo_id, filename=filename, local_dir=output_dir, local_dir_use_symlinks=False, revision="main")

    def download_repo(self,repo_id, output_dir="model"):
        """
        Download a full repo from a given HuggingFace repository.
        """
        snapshot_download(repo_id=repo_id,local_dir="output_dir",local_dir_use_symlinks=False, revision="main")


class DockerizedLLMServingSystem:
    """Creates an image to serve a specific model into a docker container. 
    It uses llama.cpp as the backend for the model. 
    The model will use as an OpenAPI compatible API endpoint the API implemented by the llama.cpp project.(Source: https://github.com/abetlen/llama-cpp-python?tab=readme-ov-file#openai-compatible-web-server).

    Requirements:
    - a docker deamon installed on the current machine (to build the image)

    Keyword arguments:
    build_type -- parameter used by llama.cpp for when building the repository,possible values : [None, "openblas", (soon: "clblast", "cuda")]
"""

    def __init__(self, model_filename, docker_image_name, docker_image_tag,
                 preload_model=False, build_type=None, compile_backends=None, is_embedding=False, **kwargs):
        #self.model_path = model_path
        self.model_filename = model_filename
        # self.quantization_technique = quantization_technique
        self.docker_image_name = docker_image_name
        self.docker_image_tag = docker_image_tag
        self.preload_model = preload_model
        self.build_type = build_type
        self.compile_backends = compile_backends
        self.kwargs = kwargs
        self.is_embedding = is_embedding

    def get_backend(self):
        """Map the argument build_type to the llama.cpp corresponding argument.
        """
        
        if self.build_type == None:
            return ""
        elif self.build_type == "openblas":
            return "LLAMA_OPENBLAS=1"

    def format_dockerfile(self):
        """Format the dockerfile using the variables of the class.
        """
        cmd = ["python3","-m","llama_cpp.server","--model", self.model_filename]
        if self.is_embedding:
            cmd.append("--embedding")
        return f"""
# Use an official Ubuntu as a parent image
FROM debian:bookworm

# Update apt package index and install necessary packages
RUN apt-get update && apt-get install -y \
    git \
    make \
    build-essential \
    ccache \
    python3 \
    python3-pip

# Change working directory to /root/
WORKDIR /root/

# Clone the llama.cpp repository
RUN git clone https://github.com/ggerganov/llama.cpp

# Change working directory to /root/llama.cpp
WORKDIR /root/llama.cpp

RUN git reset --hard f139d2ea611c5604395c95160d3c53f7c4eaf220

# Install Python requirements
RUN pip install -r requirements.txt --break-system-packages

# Build llama.cpp with debug flag
RUN make LLAMA_DEBUG=1 {self.get_backend()}

# Install llama-cpp-python[server]
RUN pip install 'llama-cpp-python[server]' --break-system-packages

# Copy the GGUF model from the host into the container
COPY {self.model_filename} /root/llama.cpp/

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=2600

# Expose port 2600
EXPOSE 2600

# Start llama_cpp server
CMD {cmd}
"""


    def build_image(self):
        """Build the image using the dockerfile formatted by the method format_dockerfile().
        """
        import subprocess

        with open('Dockerfile', 'w') as f:
            f.write(self.format_dockerfile())

        subprocess.run(["docker","buildx", "build","--progress=plain",f"--tag={self.docker_image_name}:{self.docker_image_tag}",'.'])

#----------------------
# MAIN
#----------------------

if __name__ == "__main__":

    # Arguments
    parser = get_parser()
    args = parser.parse_args()
    docker_image_name = args.image_name
    docker_image_tag = args.image_tag
    build_type = args.build_type # Check the summary of the class DockerizedLLMServingSystem for more details about the possible values.
    is_embedding = args.embeddings is not None

    # Download a gguf model
    hf = HuggingFaceInterface(authenticate=False)

    # User interaction to search and download a model
    while True:
        name = input('Welcome to Hugging Face Model Search\nEnter the name or keyword of the model you are looking for: ')
        tag = input('Enter a tag (optional; e.g., "gguf", "llama"): ')
        print("Here are all repository found:")
        hf.search_repo_in_hub(name, tag)
        retry = input("Do you want to perform another search? (y/n): ").lower()
        if retry != "y":
            break

    while True:
        repo_id = input('Enter the repository ID you want to explore: ')
        if hf.repo_exists(repo_id):
            break
        else:
            print("FAILED : The repository you are trying to access does not exist or you do not have permission to view it. Please check the repository ID and try again. Note that you may need to log in to access the repository.")
    
    print("Here are the GGUF files in this repository:")
    hf.list_gguf_files_in_repo(repo_id)

    while True:
        filename = input("Enter the filename of the model you want to download: ")
        if hf.file_exists(repo_id,filename):
            break
        else:
            print("FAILED : The file you are trying to download does not exist or you do not have permission to acces the repository. Please check all the IDs and try again. Note that you may need to log in to access the repository.")
            sys.exit(1)

    print("Initiating download process...")
    hf.download_file(repo_id, filename, output_dir=".")

    # Build the image
    system = DockerizedLLMServingSystem(filename, docker_image_name, docker_image_tag, build_type, is_embedding)
    system.build_image()