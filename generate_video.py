import moviepy.editor as mp
import math
from PIL import Image
import numpy
import sys
import pysrt


def create_srt_file(script_list, output_file):
    with open(output_file, "w") as file:
        count = 1
        for index, word_dict in enumerate(script_list):
            start_time = format_time(word_dict["start_time"])
            stop_time = format_time(word_dict["end_time"])
            subtitle = f"{count}\n{start_time} --> {stop_time}\n{word_dict['word']}\n\n"
            file.write(subtitle)
            count += 1


def format_time(time):
    seconds = int(time)
    milliseconds = int((time - seconds) * 1000)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, seconds, milliseconds)


def time_to_seconds(time_obj):
    return (
        time_obj.hours * 3600
        + time_obj.minutes * 60
        + time_obj.seconds
        + time_obj.milliseconds / 1000
    )


def create_subtitle_clips(
    subtitles, videosize, fontsize=90, font="Rockwell-Bold", color="white", debug=False
):
    subtitle_clips = []

    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time = time_to_seconds(subtitle.end)
        duration = end_time - start_time

        video_width, video_height = videosize

        text_clip = (
            mp.TextClip(
                subtitle.text,
                fontsize=fontsize,
                font=font,
                color=color,
                stroke_color="black",
                stroke_width=3,
                size=(video_width * 3 / 4, None),
                method="caption",
            )
            .set_start(start_time)
            .set_duration(duration)
        )
        subtitle_x_position = "center"
        subtitle_y_position = video_height * 2 / 5

        text_position = (subtitle_x_position, subtitle_y_position)
        subtitle_clips.append(text_clip.set_position(text_position))

    return subtitle_clips


def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size

        new_size = [
            math.ceil(img.size[0] * (1 + (zoom_ratio * t))),
            math.ceil(img.size[1] * (1 + (zoom_ratio * t))),
        ]

        # The new dimensions must be even.
        new_size[0] = new_size[0] + (new_size[0] % 2)
        new_size[1] = new_size[1] + (new_size[1] % 2)

        img = img.resize(new_size, Image.LANCZOS)

        x = math.ceil((new_size[0] - base_size[0]) / 2)
        y = math.ceil((new_size[1] - base_size[1]) / 2)

        img = img.crop([x, y, new_size[0] - x, new_size[1] - y]).resize(
            base_size, Image.LANCZOS
        )

        result = numpy.array(img)
        img.close()

        return result

    return clip.fl(effect)


def stitch_video(
    scenes, audio_file, srt_file, output_file_name, final_size=(1080, 1920)
):
    slides = []
    for n, scene in enumerate(scenes):
        slides.append(
            mp.ImageClip(scene["image_path"])
            .set_fps(30)
            .set_duration(scene["end_time"] - scene["start_time"])
            .resize(final_size)
        )

        slides[n] = zoom_in_effect(slides[n], 0.04)

    final_clip = mp.concatenate_videoclips(slides)

    subtitles = pysrt.open(srt_file)

    subtitle_clips = create_subtitle_clips(subtitles, final_clip.size)

    # Add subtitles to the video
    final_video = mp.CompositeVideoClip([final_clip] + subtitle_clips)

    # Load audio file
    audio = mp.AudioFileClip(audio_file)

    # Set the audio of the final clip
    final_video.audio = audio

    # Write the result to a file (remember to adjust the fps as per your requirement)
    final_video.write_videofile(output_file_name, codec="libx264", audio_codec="aac")
