#######################
### IMPORT PACKAGES ###
#######################

import pandas as pd
import re
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from io import StringIO
from typing import List, Optional, Dict, Tuple
import json
from IPython.display import clear_output

# Load in regex patterns for company names
from resources.regex_company_patterns import company_regex_dict

COMPANY_REGEX_DICT = company_regex_dict

#############
### PATHS ###
#############

fp_main = Path("/Volumes/SAM-SODAS-DISTRACT/Coding Distraction/github_as_market_device")
fp_output = fp_main / "output"

# Pre-defined location filter string
filter_string = (
    "type:user&org location:dk location:Denmark location:Danmark "
    "location:CPH location:KBH location:Copenhagen location:Cop "
    "location:København location:Odense location:Aarhus location:Århus "
    "location:Aalborg location:Ålborg location:Esbjerg location:Randers "
    "location:Kolding location:Horsens location:Vejle location:Roskilde "
    "location:Herning"
)

#################
### FUNCTIONS ###
#################


def match_location_filter_string(user_location: str) -> List[str]:
    """
    Match user location against known Danish city/location terms using regex.

    Args:
        user_location (str): User-provided location string.

    Returns:
        List[str]: Matching DK location keywords.
    """
    dk_locations = [
        i.replace("location:", "") for i in filter_string.split(" ") if "location:" in i
    ]
    pattern = re.compile(
        rf"\b({'|'.join(map(re.escape, dk_locations))})\b", re.IGNORECASE
    )
    return pattern.findall(user_location)


def check_if_unkwn_city_in_dk(geo_search: requests.Response) -> bool:
    """
    Check if the response from GeoNames corresponds to a location in Denmark.

    Args:
        geo_search (requests.Response): HTTP response object from GeoNames.

    Returns:
        bool: True if location is in Denmark, else False.
    """
    soup = BeautifulSoup(geo_search.text, "lxml")
    table = soup.find("table", {"class": "restable"})
    if not table:
        return False

    try:
        df = pd.read_html(StringIO(str(table)), header=1, index_col=0)[0]
        country = df["Country"].iloc[1]
        return bool(re.search(r"denmark", str(country), re.IGNORECASE))
    except Exception:
        return False


def look_up_if_location_in_dk(location: str) -> Optional[List[str]]:
    """
    Look up unknown location strings to check if any refer to Denmark.

    Args:
        location (str): Free-text location string.

    Returns:
        Optional[List[str]]: List of matching DK tags, if any.
    """
    cities = [city.strip(",") for city in location.split()]
    geo_tags_in_dk = []

    for city in cities:
        if city and not city.isnumeric():
            try:
                response = requests.get(
                    f"https://www.geonames.org/search.html?q={city}&country="
                )
                if check_if_unkwn_city_in_dk(response):
                    geo_tags_in_dk.append(city)
            except requests.RequestException:
                continue

    return geo_tags_in_dk if geo_tags_in_dk else None


def user_is_from_dk(
    bio_variables: List[str], user_location: Optional[str]
) -> Optional[List[str]]:
    """
    Determine whether a user is likely from Denmark based on bio/location.

    Args:
        bio_variables (List[Optional[str]]): Other strings from user bio (can include None).
        user_location (Optional[str]): The location field from user profile.

    Returns:
        Optional[List[str]]: Matching DK location keywords or None.
    """
    # Ensure all values are strings and filter out None
    safe_bio = [str(item) for item in bio_variables if item]
    safe_location = str(user_location) if user_location else ""

    combined_text = " ".join(safe_bio + [safe_location])
    match = match_location_filter_string(combined_text)

    if match:
        return match
    elif safe_location:
        return look_up_if_location_in_dk(safe_location)
    return None


def search_for_company(bio_variables: List[str]) -> Optional[Dict[str, List[str]]]:
    """
    Identify company names in a list of strings using predefined regex patterns.

    Args:
        bio_variables (List[str]): List of strings (e.g. user bio fields).

    Returns:
        Optional[Dict[str, List[str]]]: Matches by company, or None.
    """
    matches = {}

    for company, pattern in company_regex_dict.items():
        regex = re.compile(pattern, re.IGNORECASE)
        found = [bio for bio in bio_variables if regex.search(bio)]
        if found:
            matches[company] = found

    return matches if matches else None


def infer_if_dk_and_company(
    user_login: str,
    company: str | None,
    email: str | None,
    bio: str | None,
    blog: str | None,
    location: str | None,
) -> Optional[Tuple[List[str], Dict[str, List[str]]]]:
    """
    Return both DK location matches and company matches from user fields.

    Args:
        user_login (str | None): The login name of the user.
        company (str | None): The company name.
        email (str | None): The email address.
        bio (str | None): The user bio.
        blog (str | None): The user blog URL.
        location (str | None): The user location.

    Returns:
        A tuple of:
            - DK location matches (list of str)
            - company matches: Dict[company_name, List[str (matched text)]]
    """
    bio_variables_bundle = [user_login, company, email, bio, blog]
    bio_variables_clean = [str(bio.lower()) for bio in bio_variables_bundle if bio]

    # Check if from Denmark
    location_result = user_is_from_dk(bio_variables_clean, location)
    if not location_result:
        return None

    # Search for company matches
    matched_companies = search_for_company(bio_variables_clean)
    if not matched_companies:
        return None

    return location_result, matched_companies


########################################################
### Function to filter unique ties for a GitHub user ###
########################################################


def filter_ties(row, ties_columns):
    """
    Given a row and a list of column names, extract and filter all tied users,
    excluding the user themselves. Works for lists of strings or dicts with 'owner_login'.

    Args:
        row (pd.Series): The row of the DataFrame containing user data.
        ties_columns (list): List of column names to check for ties.

    Returns:
        list: A list of unique tied user logins.
    """
    all_ties = []

    # Iterate over each column to find ties
    for col in ties_columns:
        val = row.get(col)

        # Check if the value is a list
        if isinstance(val, list):
            if len(val) == 0:
                continue

            # Check if the first element is a dict
            if isinstance(val[0], dict):
                all_ties.extend(
                    [
                        item.get("owner_login")
                        for item in val
                        if item.get("owner_login")
                        and item.get("owner_login") != row["user_login"]
                    ]
                )
            # Check if the first element is a string
            elif isinstance(val[0], str):
                all_ties.extend([user for user in val if user != row["user_login"]])

    return list(set(all_ties))


###################################################
### Functionality to resolve multiple companies ###
###################################################


def resolve_multiple_companies(df: pd.DataFrame, output_path: str) -> pd.DataFrame:
    """
    Resolve ambiguous inferred companies in a DataFrame by:
    - Automatically reducing single-element lists to strings.
    - Prompting the user for manual resolution of multiple matches.
    - Skipping entries if no input is provided.

    Args:
        df (pd.DataFrame): The DataFrame containing user data.
        output_path (str): The path to the output file for resolved companies.

    Returns:
        pd.DataFrame: The updated DataFrame with resolved companies.
    """
    resolved_users = _load_resolved_users(output_path)

    try:
        for idx, row in df.iterrows():
            user_login = row["user_login"]
            inferred = row["inferred_company"]

            # Skip if already resolved
            if user_login in resolved_users:
                df.at[idx, "inferred_company"] = resolved_users[user_login]
                continue

            # If it's a single-item list, auto-resolve to string
            if isinstance(inferred, list):
                if len(inferred) == 1:
                    df.at[idx, "inferred_company"] = inferred[0]
                    continue
                elif len(inferred) > 1:
                    resolved_company = _prompt_user_to_resolve(row)
                    if resolved_company:
                        df.at[idx, "inferred_company"] = resolved_company
                        resolved_users[user_login] = resolved_company
                        _save_resolved_company(
                            output_path, user_login, resolved_company
                        )
                    else:
                        print("Skipped. No changes saved for this user.")
    except KeyboardInterrupt:
        print("\n[INFO] Annotation manually interrupted. Exiting safely.")

    return df


def _load_resolved_users(output_path: str) -> dict:
    """
    Load previously resolved users from JSONL.

    Args:
        output_path (str): The path to the output file for resolved companies.

    Returns:
        dict: A dictionary mapping user logins to their resolved companies.
    """
    resolved = {}
    path = Path(output_path)

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                resolved[entry["user_login"]] = entry["resolved_company"]

    return resolved


def _save_resolved_company(
    output_path: str, user_login: str, resolved_company: str
) -> None:
    """
    Append a resolved company annotation to the JSONL file.

    Args:
        output_path (str): The path to the output file for resolved companies.
        user_login (str): The user login to resolve.
        resolved_company (str): The resolved company name.

    Returns:
        None
    """
    with open(output_path, "a", encoding="utf-8") as f:
        json.dump({"user_login": user_login, "resolved_company": resolved_company}, f)
        f.write("\n")


def _prompt_user_to_resolve(row: pd.Series) -> str:
    """
    Display relevant user info and prompt for resolution (Jupyter-friendly, clears prior output).

    Args:
        row (pd.Series): The DataFrame row containing user information.

    Returns:
        str: The resolved company name or an empty string if skipped.
    """
    user_login = row["user_login"]

    # Clear previous output
    clear_output(wait=True)

    # Display new output
    print("=" * 50)
    print(f"[{user_login}] has multiple company matches:")
    print(f"Inferred Companies: {row['inferred_company']}")

    print("\nMatched Strings:")
    for company, matches in row.get("matched_company_strings", {}).items():
        print(f"  {company}: {matches}")

    print("\nBio Information:")
    for col in [
        "user_login",
        "search_with_company",
        "usertype",
        "listed_company",
        "email",
        "bio",
        "blog",
    ]:
        print(f"  {col}: {row.get(col, '')}")

    return input(
        "\nType the correct company for this user (or press Enter to skip): "
    ).strip()


##################################################################
### Filter function to look-up companies in edgelist Dataframe ###
##################################################################


def look_company_up_in_edgelist(
    company: str,
    edgelist: pd.DataFrame,
    alternative_company: Optional[str] = None,
    direction: str = "all",
    exclude_self_loops: bool = True,
) -> pd.DataFrame:
    """
    Looks up a company in the edgelist DataFrame and filters the edges accordingly.

    Args:
        company (str): The company name to look up.
        edgelist (pd.DataFrame): The edgelist DataFrame to filter.
        alternative_company (Optional[str]): An optional second company name to look up.
        direction (str): The direction of the edges to consider ('in', 'out', or 'all').
        exclude_self_loops (bool): Whether to exclude self-loops (intra-company ties).

    Returns:
        pd.DataFrame: The filtered edgelist DataFrame.
    """

    # Filter edgelist looking up one company
    if company and not alternative_company:
        one_company_mask = (edgelist["src_company"] == company) | (
            edgelist["target_company"] == company
        )
        edgelist = edgelist[one_company_mask].copy()

    # Filter edgelist looking up two companies
    elif company and alternative_company:
        two_company_mask = (
            (edgelist["src_company"] == company)
            & (edgelist["target_company"] == alternative_company)
        ) | (
            (edgelist["src_company"] == alternative_company)
            & (edgelist["target_company"] == company)
        )
        edgelist = edgelist[two_company_mask].copy()

    # Filter edgelist for self-loops (intra-company ties) or not
    if exclude_self_loops:
        edgelist = edgelist[
            edgelist["src_company"] != edgelist["target_company"]
        ].copy()

    # Filter edgelist for direction
    if direction == "out":
        edgelist = edgelist[edgelist["src_company"] == company].copy()
    elif direction == "in":
        edgelist = edgelist[edgelist["target_company"] == company].copy()
    elif direction == "all":
        pass
    else:
        raise ValueError("Invalid direction specified. Use 'in', 'out', or 'all'.")

    return edgelist
