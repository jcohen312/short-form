import guidance
import re
import requests
import time
import os
from config import open_ai_key, leonardo_ai_auth


def extract_text_between_quotes(string):
    pattern = r'"([^"]*)"'
    matches = re.findall(pattern, string)
    return matches[0]


os.environ["OPENAI_API_KEY"] = open_ai_key

guidance.llm = guidance.llms.OpenAI("text-davinci-003")


opening_scene_maker = guidance(
    """The following is a scene for a Tik Tok video in JSON format. The scene description item contains a string describing the scene of the video in detail. It will eventually be used as an input into an AI tool to generate still images that will serve as the visuals for the video.

```json
{
    "start_time": "{{start_time}}",
    "end_time": "{{end_time}}",
    "scene_script": "{{scene_script}}",
    "scene_description": {{gen 'scene_description' temperature=0.7}}
}```

based on the following script:

{{script}}
"""
)


subsequent_scene_maker = guidance(
    """The last scene in a tiktok video is {{last_scene}}.

The following is the next scene for the video in JSON format which is based on the text from scene_script, the text from the script that makes up the scene in the video. The scene description item contains a string describing the scene of the video in detail. It will eventually be used as an input into an AI tool to generate still images that will serve as the visuals for the video.


json
{
    "start_time": "{{start_time}}",
    "end_time": "{{end_time}}",
    "scene_script": "{{scene_script}}",
    "scene_description": {{gen 'scene_description' temperature=0.7}}
    }

based on the following script:

{{script}}
"""
)


def run_scene_generator(scenes_with_times, full_script_text):
    output = []

    for idx, scene in enumerate(scenes_with_times):
        if idx == 0:
            first_scene = opening_scene_maker(
                start_time=scene["start_time"],
                end_time=scene["end_time"],
                scene_script=scene["scene_script"],
                script=full_script_text,
            )
            d = first_scene.variables()

            d["scene_description"] = extract_text_between_quotes(d["scene_description"])

            output.append(d)

        else:
            subsequent_scene = subsequent_scene_maker(
                last_scene=output[idx - 1]["scene_description"],
                start_time=scene["start_time"],
                end_time=scene["end_time"],
                scene_script=scene["scene_script"],
                script=full_script_text,
            )

            d = subsequent_scene.variables()

            d["scene_description"] = extract_text_between_quotes(d["scene_description"])

            output.append(d)

    for item in output:
        if "llm" in item:
            del item["llm"]

    return output


prompt_generator = guidance(
    """The following are rules to generate prompts for a generative AI called "Leonardo AI". Leonardo AI generates images based on given prompts. The information required to make a Stable Diffusion prompt is the following and the structure never deviates.

Basic information required to make Leonardo AI prompt:

- Prompt structure:

- Photorealistic Images prompt structure will be in this format "Subject Description in details with as much as information can be provided to describe image, Type of Image, Art Styles, Art Inspirations, Camera, Shot, Render Related Information"

- Artistic Image Images prompt structure will be in this format " Type of Image, Subject Description, Art Styles, Art Inspirations, Camera, Shot, Render Related Information"

- Word order and effective adjectives matter in the prompt. The subject, action, and specific details should be included. Adjectives like cute, medieval, or futuristic can be effective.

- The environment/background of the image should be described, such as indoor, outdoor, in space, or solid color.

- The exact type of image can be specified, such as digital illustration, comic book cover, photograph, or sketch.

- Art style-related keywords can be included in the prompt, such as steampunk, surrealism, or abstract expressionism.

- Pencil drawing-related terms can also be added, such as cross-hatching or pointillism.

- Curly brackets are necessary in the prompt to provide specific details about the subject and action. These details are important for generating a high-quality image.

- Art inspirations should be listed to take inspiration from. Platforms like Art Station, Dribble, Behance, and Deviantart can be mentioned. Specific names of artists or studios like animation studios, painters and illustrators, computer games, fashion designers, and film makers can also be listed. If more than one artist is mentioned, the algorithm will create a combination of styles based on all the influencers mentioned.

- Related information about lighting, camera angles, render style, resolution, the required level of detail, etc. should be included at the end of the prompt.

- Camera shot type, camera lens, and view should be specified. Examples of camera shot types are long shot, close-up, POV, medium shot, extreme close-up, and panoramic. Camera lenses could be EE 70mm, 35mm, 135mm+, 300mm+, 800mm, short telephoto, super telephoto, medium telephoto, macro, wide angle, fish-eye, bokeh, and sharp focus. Examples of views are front, side, back, high angle, low angle, and overhead.

- Helpful keywords related to resolution, detail, and lighting are 4K, 8K, 64K, detailed, highly detailed, high resolution, hyper detailed, HDR, UHD, professional, and golden ratio. Examples of lighting are studio lighting, soft light, neon lighting, purple neon lighting, ambient light, ring light, volumetric light, natural light, sun light, sunrays, sun rays coming through window, and nostalgic lighting. Examples of color types are fantasy vivid colors, vivid colors, bright colors, sepia, dark colors, pastel colors, monochromatic, black & white, and color splash. Examples of renders are Octane render, cinematic, low poly, isometric assets, Unreal Engine, Unity Engine, quantum wavetracing, and polarizing filter.

- The weight of a keyword can be adjusted by using the syntax (((keyword))) , put only those keyword inside ((())) which is very important because it will have more impact so anything wrong will result in unwanted picture so be careful.



Prompts are provided in English. Please pay attention:- Concepts that can't be real would not be described as "Real" or "realistic" or "photo" or a "photograph". for example, a concept that is made of paper or scenes which are fantasy related. a lens type and size should be provided. Artists should not be chosen for the realistic photography prompts.



The following is a prompt for this scene that describes a still image that will be used to generate the imagery for a tik tok video:

scene: {{scene}}
prompt: {{gen 'prompt' temperature=0.1}}



"""
)


def generate_image_prompts(scenes_with_descriptions_list):
    for scene_with_description in scenes_with_descriptions_list:
        print(scene_with_description["scene_description"])

        image_prompt = prompt_generator(
            scene=scene_with_description["scene_description"]
        )

        prompt_var = image_prompt.variables()["prompt"]

        scene_with_description["prompt"] = prompt_var

    return scenes_with_descriptions_list


def generate_image(prompt):
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"

    payload = {
        "prompt": prompt,
        "modelId": "b7aa9939-abed-4d4e-96c4-140b8c65dd92",
        "width": 832,
        "height": 1472,
        # "sd_version": "v2",
        "promptMagic": True,
        "num_images": 1,
        "negative_prompt": """double image, repitition, double, double body, double face, double features, incorrect posture, two heads, two faces, Deformed, blurry, bad anatomy,  disfigured, poorly drawn face, mutation, mutated, {{extra limb}}, ugly, poorly drawn hands, missing limb, blurry, floating limbs, disconnected limbs, malformed hands, blur, out of focus, long neck, long body, {{{mutated hands and fingers}}}, {{{out of frame}}}, long fingers, cropped, low-res,  poorly-drawn face, out of frame double, two heads, blurred, ugly, disfigured, too many fingers, deformed, repetitive, grainy, extra limbs, bad anatomy, High pass filter,  closeup, deformed, extra limbs, extra fingers, mutated hands, bad anatomy, bad proportions ,  bad eyes, ugly eyes, dead eyes, blur, out of shot, out of focus, gaussian,""",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": leonardo_ai_auth,
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.json()


def download_image(generationId, base_path):
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generationId}"

    headers = {
        "accept": "application/json",
        "authorization": leonardo_ai_auth,
    }

    response = requests.get(url, headers=headers)

    response_json = response.json()

    image_url = response_json["generations_by_pk"]["generated_images"][0]["url"]

    image_path = base_path + "/" + generationId + ".jpeg"

    def download_image(url, save_path):
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful

        with open(save_path, "wb") as file:
            file.write(response.content)

        print(f"Image downloaded and saved as {save_path}")

    download_image(image_url, image_path)

    return response_json, image_path


def image_generator(scenes_with_prompts_json, path):
    new_json = []

    for scene in scenes_with_prompts_json:
        image_generation = generate_image(scene["prompt"])

        gen_id = image_generation["sdGenerationJob"]["generationId"]

        print(gen_id)

        time.sleep(20)

        leoai_json, img = download_image(gen_id, path)

        scene["image_generation_info"] = leoai_json

        scene["image_path"] = img

        new_json.append(scene)

    return new_json
