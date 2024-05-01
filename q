[1mdiff --git a/main.py b/main.py[m
[1mindex 65846d1..bdac8ca 100644[m
[1m--- a/main.py[m
[1m+++ b/main.py[m
[36m@@ -1,5 +1,19 @@[m
 """[m
[31m-TODO : Quick Introduction[m
[32m+[m[32mThis python module meet the following requirements :[m
[32m+[m[32m-> Check HuggingFace for gguf models and download them.[m
[32m+[m[32m-> Serve the model with llama.cpp[m[41m [m
[32m+[m[32m-> Serve the model with an OpenAI endpoint API.[m
[32m+[m[32m-> Dockerize the whole[m[41m [m
[32m+[m
[32m+[m[32m# VERSION[m
[32m+[m
[32m+[m[32mVERSION : 1.0[m
[32m+[m
[32m+[m[32m# CONFIG[m
[32m+[m
[32m+[m[32mBACKEND : llama.cpp from source[m
[32m+[m[32mAPI : Built-in llama.cpp API (python module "llama-cpp-python[server]")[m
[32m+[m
 """[m
 [m
 [m
[36m@@ -250,7 +264,23 @@[m [mCMD ["python3", "-m", "llama_cpp.server", "--model={self.model_filename}"][m
 #----------------------[m
 [m
 if __name__ == "__main__":[m
[32m+[m[32m    """For testing, here is a scenario in which the user is asked to choose a GGUF model from the HuggingFace Hub, then it creates the docker image to serve the model chosen.[m
[32m+[m[32m    When the image is built succesfully, you can run a first container with the following command :[m
[32m+[m[41m    [m
[32m+[m[32m        docker run -dit -p 2600:2600 <docker_image_name>:<docker_image_tag>[m
 [m
[32m+[m[32m    And then your model is served into this container and is accessible through a OpenAI compatible API.[m
[32m+[m
[32m+[m[32m    Example for testing :[m
[32m+[m
[32m+[m[32m        1. Retrieve the id of the model with the following command:[m
[32m+[m[32m        curl http://localhost:2600/v1/models -H 'Content-Type: application/json'[m
[32m+[m
[32m+[m[32m        2. Send a chat completion request to the served model using the following command:[m
[32m+[m[32m        curl http://localhost:2600/v1/chat/completions -H 'Content-Type: application/json' -d '{"model": "<model_id_found_with_the_previous_command>", "messages": [{"role": "user", "content": "Are you loaded ?"}], "temperature": 0.9, "max_tokens":25}'[m
[32m+[m
[32m+[m[32m    """[m
[32m+[m[41m    [m
     # Arguments[m
     docker_image_name = "imagetest"[m
     docker_image_tag = "tagtest"[m
