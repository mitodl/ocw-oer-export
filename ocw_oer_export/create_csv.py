"""
Module for creating OER-template CSV file with data extracted from MIT OpenCourseWare API.
"""
import csv
import os.path
import logging
import pandas as pd

from .client import extract_data_from_api
from .data_handler import extract_data_from_json
from .constants import API_URL
from .utilities import cleanup_curly_brackets, html_to_text, markdown_to_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_ocw_topic_to_oer_subject_mapping(path=None, file_name=None):
    """Returns a mapping (dictionary) of OCW topics to OER subjects."""
    if path is None:
        path = os.path.dirname(__file__)

    if file_name is None:
        file_name = "mapping_files/ocw_topic_to_oer_subject.csv"

    file_path = os.path.join(path, file_name)
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return {row["OCW Topic"]: row["OER Subject"] for row in reader}


def get_cr_subjects(ocw_topics_mapping, ocw_course_topics):
    """Get Course Resource Subjects based on OCW topics."""
    oer_subjects_list = [
        ocw_topics_mapping.get(topic["name"]).split("|")
        if ocw_topics_mapping.get(topic["name"]) is not None
        else []
        for topic in ocw_course_topics
    ]
    unique_oer_subjects = set(
        subject for subjects in oer_subjects_list for subject in subjects
    )
    return "|".join(unique_oer_subjects)


def get_cr_keywords(list_of_topics_objs):
    """Get Course Resource Keywords from a list of OCW topic objects."""
    return "|".join(topic["name"] for topic in list_of_topics_objs)


def get_cr_authors(list_of_authors_objs):
    """Get Course Resource Authors from a list of OCW author objects."""
    return "|".join(
        f"{author['last_name']}, {author['first_name']}"
        for author in list_of_authors_objs
    )


def get_cr_educational_use(course_feature_tags):
    """Get Course Resource Educational Use based on course feature tags."""
    tags = ["Curriculum/Instruction"]
    assessment_flag = any("Assignment" in tag for tag in course_feature_tags)
    professional_dev_flag = "Instructor Insights" in course_feature_tags

    if assessment_flag:
        tags.append("Assessment")

    if professional_dev_flag:
        tags.append("Professional Development")

    return "|".join(tags)


def get_cr_accessibility(course_feature_tags):
    """Get Course Resource Accessibility tags based on course feature tags."""
    tags = ["Visual|Textual"]
    video_flag = any("Video" in tag for tag in course_feature_tags)

    if video_flag:
        tags.append("Auditory|Caption|Transcript")

    return "|".join(tags)


def get_description_in_plain_text(description):
    """Get Course Resource plain text description by cleaning up markdown and HTML."""
    stripped_markdown = markdown_to_text(description)
    stripped_html = html_to_text(stripped_markdown)
    plain_description = cleanup_curly_brackets(stripped_html)
    return plain_description


def transform_single_course(course, ocw_topics_mapping):
    """Transform a single course according to OER template."""
    if course.get("runs"):
        return {
            "CR_TITLE": course["title"],
            "CR_URL": course["runs"][0]["url"],
            "CR_MATERIAL_TYPE": "Full Course",
            "CR_Media_Formats": "Text/HTML",
            "CR_ABSTRACT": get_description_in_plain_text(
                course["runs"][0]["description"]
            ),
            "CR_LANGUAGE": "en",
            "CR_COU_TITLE": "Creative Commons Attribution Non Commercial Share Alike 4.0",
            "CR_PRIMARY_USER": "student|teacher",
            "CR_SUBJECT": get_cr_subjects(ocw_topics_mapping, course["topics"]),
            "CR_KEYWORDS": get_cr_keywords(course["topics"]),
            "CR_AUTHOR_NAME": get_cr_authors(course["runs"][0]["instructors"]),
            "CR_PROVIDER": "MIT",
            "CR_PROVIDER_SET": "MIT OpenCourseWare",
            "CR_COU_URL": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "CR_COU_COPYRIGHT_HOLDER": "MIT",
            "CR_EDUCATIONAL_USE": get_cr_educational_use(course["course_feature"]),
            "CR_ACCESSIBILITY": get_cr_accessibility(course["course_feature"]),
        }
    return None


def transform_data(data, ocw_topics_mapping):
    """Transform all courses into OER template."""
    return [
        course
        for course in (
            transform_single_course(course, ocw_topics_mapping) for course in data
        )
        if course is not None
    ]


def create_csv(source="api", output_file="ocw_oer_export.csv"):
    """Create a CSV file from either the MIT OpenCourseWare API or a locally stored JSON file."""
    if source == "api":
        api_data_json = extract_data_from_api(api_url=API_URL)

    elif source == "json":
        api_data_json = extract_data_from_json("ocw_api_data.json")

    else:
        raise ValueError("Invalid source. Use 'api' or 'json'.")

    ocw_topics_mapping = create_ocw_topic_to_oer_subject_mapping()
    transformed_data = transform_data(api_data_json, ocw_topics_mapping)
    columns = [
        "CR_TITLE",
        "CR_URL",
        "CR_MATERIAL_TYPE",
        "CR_Media_Formats",
        "CR_ABSTRACT",
        "CR_LANGUAGE",
        "CR_COU_TITLE",
        "CR_PRIMARY_USER",
        "CR_SUBJECT",
        "CR_KEYWORDS",
        "CR_AUTHOR_NAME",
        "CR_PROVIDER",
        "CR_PROVIDER_SET",
        "CR_COU_URL",
        "CR_COU_COPYRIGHT_HOLDER",
        "CR_EDUCATIONAL_USE",
        "CR_ACCESSIBILITY",
    ]
    final_df = pd.DataFrame(transformed_data, columns=columns)
    final_df.to_csv(output_file, index=False)
    logger.info("CSV file %s successfully created at present directory.", output_file)
