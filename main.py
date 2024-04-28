"""
TODO : Quick Introduction
"""


#----------------------
# Dependencies
#----------------------

import logging, io, re, requests, docker
from huggingface_hub import login
from huggingface_hub import get_hf_file_metadata, hf_hub_url, repo_info, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError, RevisionNotFoundError
from typing import Optional

#----------------------
# CONFIG
#----------------------

logging.basicConfig(level=logging.INFO)

GO_URL = "https://go.dev/dl/go1.21.1.linux-amd64.tar.gz"

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
        res = requests.get(url)
        for model in res.json():
            if re.match("^\s*$",tag):
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
        hf_hub_download(repo_id=repo_id, filename=filename, local_dir=output_dir,local_dir_use_symlinks=False, revision="main")

    def search_model_and_download(self, output_dir):
        """
        Guide the user into the process flow of searching for a model in the HF Hub, and download it.
        """
        
        while True:
            name = input('Welcome to Hugging Face Model Search\nEnter the name or keyword of the model you are looking for: ')
            tag = input('Enter a tag (optional; e.g., "gguf", "llama"): ')
            print("Here are all repository found:")
            self.search_repo_in_hub(name, tag)
            retry = input("Do you want to perform another search? (y/_): ").lower()
            if retry != "y":
                break

        while True:
            repo_id = input('Enter the repository ID you want to explore: ')
            if self.repo_exists(repo_id):
                break
            else:
                print("FAILED : The repository you are trying to access does not exist or you do not have permission to view it. Please check the repository ID and try again. Note that you may need to log in to access the repository.")
        print("Here are the GGUF files in this repository:")
        self.list_gguf_files_in_repo(repo_id)
        
        while True:
            filename = input("Enter the filename of the model you want to download: ")
            if self.file_exists(repo_id,filename):
                break
            else:
                print("FAILED : The file you are trying to download does not exist or you do not have permission to acces the repository. Please check all the IDs and try again. Note that you may need to log in to access the repository.")

        print("Initiating download process...")
        self.download_file(repo_id, filename, output_dir)

        return output_dir + "/" + filename, filename

class DockerizedLLMServingSystem:
    def __init__(self, model_path, model_filename, docker_image_name, docker_image_tag,
                 preload_model=False, build_type=None, compile_backends=None, **kwargs):
        self.model_path = model_path
        self.model_filename = model_filename
        # self.quantization_technique = quantization_technique
        self.docker_image_name = docker_image_name
        self.docker_image_tag = docker_image_tag
        self.preload_model = preload_model
        self.build_type = build_type
        self.compile_backends = compile_backends
        self.kwargs = kwargs

    def build_image(self):
        dockerfile = f"""
FROM debian:bookworm

# Update package lists and install wget
RUN apt update && apt install -y wget

# Download and extract Go
RUN wget {GO_URL} && \\
    tar -C /usr/local -xzf {GO_URL}

# Add Go binaries to the PATH
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin

# Install required dependencies
RUN apt install -y cmake libgrpc-dev make protobuf-compiler-grpc python3-grpc-tools git

# Install protobuf and grpc tools for Go
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \\
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Clone LocalAI repository
RUN git clone https://github.com/go-skynet/LocalAI && \\
    cd LocalAI && \\
    make BUILD_GRPC_FOR_BACKEND_LLAMA=ON GRPC_BACKENDS=backend-assets/grpc/llama-cpp {"BUILD_TYPE="+self.build_type if self.build_type!=None else ""} build

# Copy model_name to models directory
COPY {self.model_path} LocalAI/models/

# Set working directory
WORKDIR /LocalAI

# Run LocalAI and load the model
CMD ["sh", "-c", "./local-ai --models-path=./models/ --debug=true && \\
    curl http://localhost:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{{\"model\": \"test.gguf\", \"messages\": [{{\"role\": \"user\", \"content\": \"Are you loaded ?\"}}], \"temperature\": 0.9}}'"]
"""
        if self.preload_model:
            dockerfile += f"""
# Execute curl command
CMD ["sh", "-c", "curl http://localhost:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{{\"model\": \"{self.model_filename}\", \"messages\": [{{\"role\": \"user\", \"content\": \"Are you loaded ?\"}}], \"temperature\": 0.9}}'"]
"""

        # Create a Docker client
        client = docker.from_env()

        try:
            # Build the Docker image from the Dockerfile string
            image, build_logs = client.images.build(fileobj=io.BytesIO(dockerfile.encode('utf-8')), rm=True, tag=f"{self.docker_image_name}:{self.docker_image_tag}")
            # Check if the image is successfully built
            if 'stream' in build_logs:
                print("Build logs:")
                for log in build_logs['stream'].split('\n'):
                    print(log)
                    
            # Check if any tags are associated with the image
            if image.tags:
                print(f"Successfully built image: {image.tags[0]}")
            else:
                print("No tags associated with the image.")
        except docker.errors.BuildError as e:
            print(f"Build failed: {e}")
        except docker.errors.APIError as e:
            print(f"API error: {e}")

#----------------------
# MAIN
#----------------------

if __name__ == "__main__":

    docker_image_name = "lai"
    docker_image_tag = "tag"
    preload_model = True
    # build_type = "cublas"
    # compile_backends = ["backend1", "backend2"]

    hf = HuggingFaceInterface(authenticate=False)

    model_path, model_filename = hf.search_model_and_download(output_dir=".")

    # Create instance of DockerizedLLMServingSystem
    system = DockerizedLLMServingSystem(model_path, model_filename, docker_image_name, docker_image_tag,
                                        preload_model)

    system.build_image()