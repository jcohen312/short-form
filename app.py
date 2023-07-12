import os
import json
import pickle
import datetime
import typer
from config import open_ai_key
from generate_script import (
    download_audio,
    process_audio,
    get_eleven_labs_audio,
    transcribe_audio,
)
from generate_scenes import (
    run_scene_generator,
    generate_image_prompts,
    image_generator,
    create_scene_styles,
)
from generate_video import stitch_video, create_srt_file, create_video_from_scene_styles

base_folder = "/Users/jakecohen/Development/tiktok/app_data"

os.environ["OPENAI_API_KEY"] = open_ai_key

app = typer.Typer()


@app.command()
def save_dictionary_as_json(dictionary, file_path):
    # Save the dictionary to a file
    with open(file_path, "w") as file:
        json.dump(object, file)


@app.command()
def load_json_as_dictionary(file_path):
    # Load the JSON object as a dictionary
    with open(file_path, "r") as file:
        loaded_dict = json.load(file)

    return loaded_dict


@app.command()
def save_string_as_text(string, file_path):
    # Save the string as a text file
    with open(file_path, "w") as file:
        file.write(string)


@app.command()
def load_text_as_string(file_path):
    # Load the text file as a string
    with open(file_path, "r") as file:
        loaded_string = file.read()
    print(loaded_string)
    return loaded_string


def save_obj(obj, file_path):
    # Save the dictionary to a file
    with open(file_path, "wb") as file:
        pickle.dump(obj, file)


def load_obj(file_path):
    # Load the dictionary from the file
    with open(file_path, "rb") as file:
        loaded_obj = pickle.load(file)

    return loaded_obj


def directory_location(shortcut: str):
    if shortcut == "mo":
        path = base_folder + "/motivation"

    # print(path)

    return path


@app.command()
def create_working_directory(shortcut: str):
    directory = directory_location(shortcut)
    # Get today's date
    today = datetime.date.today().strftime("%Y-%m-%d")

    today_directory = os.path.join(directory, today)

    # Check if today's subdirectory exists
    if not os.path.exists(today_directory):
        # If it doesn't exist, create it
        os.makedirs(today_directory)
        # return today_directory

    # Get the list of subdirectories in the today's subdirectory
    subdirectories = [
        name
        for name in os.listdir(today_directory)
        if os.path.isdir(os.path.join(today_directory, name))
    ]

    # Check if there are no subdirectories
    if not subdirectories:
        new_folder_name = "1"
    else:
        # Find the largest numbered folder
        largest_numbered_folder = max(subdirectories, key=lambda x: int(x))

        # Create a new folder with the name of the largest numbered folder + 1
        new_folder_name = str(int(largest_numbered_folder) + 1)

    # Create the new folder within today's subdirectory
    new_folder_path = os.path.join(today_directory, new_folder_name)
    os.makedirs(new_folder_path)

    print(new_folder_path)

    return new_folder_path


@app.command()
def generate_scenes(scenes_with_times, full_script_text, save_path):
    scenes_with_descriptions = run_scene_generator(scenes_with_times, full_script_text)

    save_obj(scenes_with_descriptions, save_path + "/scenes_with_descriptions.pkl")

    scenes_with_prompts = generate_image_prompts(scenes_with_descriptions)

    save_obj(scenes_with_prompts, save_path + "/scenes_with_prompts.pkl")

    scenes_with_images = image_generator(scenes_with_prompts, save_path)

    save_obj(scenes_with_images, save_path + "/scenes_with_images.pkl")

    return scenes_with_images


@app.command()
def make_srt_file(word_timings, output_file_name):
    create_srt_file(word_timings, output_file_name)
    print("SRT File Created")


@app.command()
def generate_video(
    scenes, audio_file, srt_file, output_file_name, final_size=(1080, 1920)
):
    stitch_video(
        scenes, audio_file, srt_file, output_file_name, final_size=(1080, 1920)
    )
    print("Video Generated")


@app.command()
def generate(
    source_link: str,
    shortcut: str,
    scene_method: str = "time",
    max_length: float = 4.5,
):
    working_directory = create_working_directory(shortcut)

    download_audio(source_link, working_directory + "/audio")

    audio_json, word_timings, scene_timings, full_script = process_audio(
        working_directory + "/audio.wav",
        scene_method=scene_method,
        max_length=max_length,
    )

    save_obj(audio_json, working_directory + "/audio_json.pkl")

    save_obj(word_timings, working_directory + "/word_timings.pkl")

    save_obj(scene_timings, working_directory + "/scene_timings.pkl")

    save_string_as_text(full_script, working_directory + "/transcribed_script.txt")

    full_scenes = generate_scenes(scene_timings, full_script, working_directory)

    make_srt_file(word_timings, working_directory + "/srt_transcript.srt")

    generate_video(
        full_scenes,
        working_directory + "/audio.wav",
        working_directory + "/srt_transcript.srt",
        working_directory + "/final_video.mp4",
    )


@app.command()
def generate_advanced(
    script_text: str,
    shortcut: str,
    voice_format: str = "custom",
    voice_id: str = "3b1SAmrWtC1EWVCpWoQF",
    speaker_image: str = "https://create-images-results.d-id.com/google-oauth2%7C103445322921472417399/drm_U1K7sfMZejIwm6ndz8u1c/image.png",
    scene_method: str = "time",
    max_scene_length: int = 4.5,
    scene_style="image",
    subtitles: str = "yes",
):
    working_directory = create_working_directory(shortcut)

    if ("youtube.com" in script_text) or ("tiktok.com" in script_text):
        print("internet source detected. downloading audio")

        download_audio(script_text, working_directory + "/audio")

        if voice_format == "custom":
            audio_json, word_timings, scene_timings, full_script = process_audio(
                working_directory + "/audio.wav",
                scene_method=scene_method,
                max_length=max_scene_length,
            )

            audio_path = get_eleven_labs_audio(
                full_script, voice_id=voice_id, base_path=working_directory
            )

        elif voice_format == "source":
            audio_path = working_directory + "/audio.wav"

    else:
        audio_path = get_eleven_labs_audio(
            script_text, voice_id=voice_id, base_path=working_directory
        )

    audio_json, word_timings, scene_timings, full_script = process_audio(
        audio_path,
        scene_method=scene_method,
        max_length=max_scene_length,
    )

    save_obj(audio_json, working_directory + "/audio_json.pkl")

    save_obj(word_timings, working_directory + "/word_timings.pkl")

    save_obj(scene_timings, working_directory + "/scene_timings.pkl")

    save_string_as_text(full_script, working_directory + "/transcribed_script.txt")

    scenes_with_styles = create_scene_styles(scene_timings, style=scene_style)

    save_obj(scenes_with_styles, working_directory + "/scenes_with_styles.pkl")

    if subtitles == "yes":
        make_srt_file(word_timings, working_directory + "/srt_transcript.srt")

        srt_file = working_directory + "/srt_transcript.srt"

    elif subtitles == "no":
        srt_file = ""

    create_video_from_scene_styles(
        scenes_with_styles,
        audio_path,
        working_directory + "/final_video.mp4",
        srt_file=srt_file,
        speaker_image=speaker_image,
    )


if __name__ == "__main__":
    app()
