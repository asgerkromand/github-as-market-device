#######################
### Import Packages ###
#######################

from github import Github
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import time as time
import configparser
import math
import logging
from typing import List, Optional, Dict

# Import GitHub types
from github.NamedUser import NamedUser
from github.Repository import Repository
from github.AuthenticatedUser import AuthenticatedUser

# Custom functions
from resources.filter_functions import infer_if_dk_and_company, user_is_from_dk, search_for_company

config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
config.read(Path(__file__).parent / "config.ini")

#############
### Paths ###
#############

fp_main_output = Path(
    "/Volumes/SAM-SODAS-DISTRACT/Coding Distraction/github_as_market_device/output"
)

##############
### Tokens ###
##############


# Function to collect GitHub access token from config
def collect_github_token(
    config: configparser.ConfigParser,
    section="github",
) -> str:
    """
    Collects the GitHub access token from the config file.

    Args:
        config (configparser.ConfigParser): The config parser instance.
        section (str): The section in the config file to read from.

    Returns:
        str: The GitHub access token.
    """
    token_key = "access_token"
    try:
        github_token = config.get(section, token_key)
        print("GitHub access token collected from config") 
    except (configparser.NoOptionError, configparser.NoSectionError):
        return ""

    return github_token


# Collect GitHub access tokens from the config file
github_access_token = collect_github_token(config)

#######################################################
### Custom Made Functions For Scraping Github Users ###
#######################################################


# Ratelimiter decorator

def ratelimiter(func):
    """
    Decorator to limit the rate of GitHub API calls,
    dynamically adjusting threshold according to current max rate.
    """

    def wrapper(*args, **kwargs):
        github_scraper = args[0]  # 'self'

        current_max_rate = github_scraper.github.rate_limiting[1]

        # Initialize attributes if missing
        if not hasattr(github_scraper, "github_max_rate"):
            github_scraper.github_max_rate = None
        if not hasattr(github_scraper, "rate_limit_threshold"):
            github_scraper.rate_limit_threshold = 0

        # Helper to map max rate to threshold
        def get_threshold(max_rate):
            if max_rate == 30:
                return 5
            elif max_rate == 5000:
                return 300
            else:
                return 200  # fallback default

        # Only print if threshold changes
        new_threshold = get_threshold(current_max_rate)
        if github_scraper.rate_limit_threshold != new_threshold:
            github_scraper.rate_limit_threshold = new_threshold
            print(f"[NEW] GitHub ratelimit threshold set to {new_threshold} (max rate: {current_max_rate})")

        github_scraper.github_max_rate = current_max_rate
        remaining_requests = github_scraper.github.rate_limiting[0]

        if remaining_requests < github_scraper.rate_limit_threshold:
            reset_timestamp = github_scraper.github.rate_limiting_resettime
            time_before_reset = reset_timestamp - time.time()
            wait_time = time_before_reset + 90  # 1.5 minutes buffer

            if wait_time > 0:
                wake_up_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + wait_time))
                print(f"[WAIT] Remaining requests: {remaining_requests}. Sleeping for {wait_time:.1f}s until {wake_up_time}")
                time.sleep(wait_time)
            else:
                print(f"[INFO] Reset time passed {abs(wait_time):.1f}s ago, skipping sleep.")

        return func(*args, **kwargs)

    return wrapper



# Dataclass
@dataclass
class GithubUser:
    """
    Represents a GitHub user and their associated data.
    """

    user_login: str | None
    search_with_company: str | None
    listed_company: str | None
    inferred_company: Optional[List[str]]
    matched_company_strings: Optional[Dict[str, List[str]]]
    usertype: str | None
    email: str | None
    github_location: str | list[str] | None
    matched_location: str | list[str] | None
    bio: str | None
    blog: str | None
    repo_names: list[str] | None
    follows_in: list[Dict[str, str]] | List[None]
    follows_out: list[Dict[str, str]] | list[None]
    watches_in: list[Dict[str, str]] | list[None]
    watches_out: list[Dict[str, str]] | list[None]
    stars_in: list[Dict[str, str]] | list[None]
    stars_out: list[Dict[str, str]] | list[None]
    forks_in: list[Dict[str, str]] | list[None]
    forks_out: list[Dict[str, str]] | list[None]


class GithubScraper:
    """
    Scrapes GitHub user data.
    """

    USERS_ATTEMPTED = 0
    USERS_SCRAPED = 0
    COMPANIES_SCRAPED = 0

    def __init__(
        self,
        access_token: str = github_access_token,
        repo_limit: int = 300,
        users_already_attempted: set[str] | None = None,
        users_already_scraped: set[str] | None = None,
        companies_already_scraped: set[str] | None = None,
        output: Path = fp_main_output,
    ):
        self.access_token = access_token
        self.github = self._set_up_auth_github(self.access_token)
        if not self.access_token:
            raise ValueError("GitHub access token is required.")
        self.github_max_rate = 0
        self.rate_limit_threshold = None  # Default rate limit
        self.reset_time_in_minutes = math.ceil(
            (self.github.rate_limiting_resettime - time.time()) / 60
        )
        self.reset_time_point = datetime.fromtimestamp(
            self.github.rate_limiting_resettime
        )
        self.filter_string = "type:user&org location:dk location:Denmark location:Danmark location:CPH location:KBH location:Copenhagen location:Cop location:København location:Odense location:Aarhus location:Århus location:Aalborg location:Ålborg location:Esbjerg location:Randers location:Kolding location:Horsens location:Vejle location:Roskilde location:Herning"
        self.users_already_scraped = (
            users_already_scraped if users_already_scraped else set()
        )
        self.repo_limit = repo_limit
        self.companies_already_scraped = (
            companies_already_scraped if companies_already_scraped else set()
        )
        self.users_already_attempted = (
            users_already_attempted if users_already_attempted else set()
        )
        self.output = output
        GithubScraper.USERS_SCRAPED = (
            len(users_already_scraped) if users_already_scraped else 0
        )
        GithubScraper.COMPANIES_SCRAPED = (
            len(companies_already_scraped) if companies_already_scraped else 0
        )
        GithubScraper.USERS_ATTEMPTED = (
            len(users_already_attempted) if users_already_attempted else 0
        )
        print(
            f"GithubScraper initialized with {len(self.companies_already_scraped)} companies and {len(self.users_already_scraped)} users already scraped."
        )

        # Setup logging
        self.setup_logging()

    def _set_up_auth_github(self, access_token) -> Github:
        """
        Set up the GitHub authentication with the current token.

        Args:
            access_token (str): The GitHub access token.

        Returns:
            Github: The authenticated GitHub instance.
        """
        self.github = Github(access_token)
        return self.github

    def setup_logging(self):
        """
        Setup the logging configuration (file-only, silent in terminal).
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.log_dir = self.output / "log"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_file = (
            self.log_dir / f"scrape_log_github_{time.strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        # Remove any existing handlers from this logger
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        # Attach only the file handler (no console handler)
        self.logger.addHandler(file_handler)
        # Also silence the root logger (optional, for libraries)
        logging.getLogger().setLevel(logging.CRITICAL + 1)

    @ratelimiter
    def get_gh_users(
        self, company_query: str, no_location_filter_bool: int
    ) -> List[tuple]:
        """
        Get GitHub users based on the company query and location filter.

        Args:
            company_query (str): The company name to search for.
            no_location_filter_bool (int): Flag to indicate if location filtering is applied.

        Returns:
            List[tuple]: A list of tuples containing user information.
        """
        filter_string = self.filter_string
        if no_location_filter_bool == 1:
            users = [
                (user_gh, company_query)
                for user_gh in [*self.github.search_users(company_query)]
            ]
        elif no_location_filter_bool == 0:
            company_query = f"{company_query} {filter_string}"
            users = [
                (user_gh, company_query)
                for user_gh in [*self.github.search_users(company_query)]
            ]
        if len([*users]) > 0:
            return users
        else:
            print(no_location_filter_bool, "- no users found")
            return users

    @ratelimiter
    def get_user(self, user_login: str) -> Optional[NamedUser | AuthenticatedUser]:
        """
        Get a GitHub user by their login.

        Args:
            user_login (str): The login of the GitHub user.

        Returns:
            Optional[NamedUser|AuthenticatedUser]: The GitHub user object or None if not found.
        """

        try:
            user = self.github.get_user(user_login)
            if user:
                return user
            else:
                self.logger.error(f"[get_user] User {user_login} not found.")
                return None
        except Exception as err:
            self.logger.error(f"[get_user] Error fetching user {user_login}: {err}")
            return None

    @ratelimiter
    def get_follows_in(
        self, user: NamedUser | AuthenticatedUser
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the followers of a user.

        Args:
            user (NamedUser|AuthenticatedUser): The user to get followers for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing follower information.
        """
        follows_in = []
        try:
            follows_in.extend(
                [
                    {
                        "repo_name": None,
                        "owner_login": follower.login,
                        "created_at": follower.created_at.date().isoformat(),
                    }
                    for follower in user.get_followers()
                ]
            )
            return follows_in
        except Exception as err:
            self.logger.error(
                f"[get_follow_in] Failed to get followers for user {user.login}: {err}"
            )
            return []

    @ratelimiter
    def get_follows_out(
        self, user: NamedUser | AuthenticatedUser
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the users that the specified user is following.

        Args:
            user (NamedUser|AuthenticatedUser): The user to get following for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing following information.
        """
        follows_out = []
        try:
            follows_out.extend(
                [
                    {
                        "repo_name": None,
                        "owner_login": follower.login,
                        "created_at": follower.created_at.date().isoformat(),
                    }
                    for follower in user.get_following()
                ]
            )
            return follows_out
        except Exception as err:
            self.logger.error(
                f"[get_follow_out] Failed to get following for user {user.login}: {err}"
            )
            return []

    @ratelimiter
    def get_all_repos(
        self, user: NamedUser | AuthenticatedUser
    ) -> Optional[List[Repository]]:
        """
        Get all repositories for a user.

        Args:
            user (NamedUser|AuthenticatedUser): The user to get repositories for.

        Returns:
            Optional[List[Repository]]: A list of repositories or None if the user has too many.
        """
        if (
            user.public_repos > self.repo_limit
        ):  # IMPORTANT methodological choice: This is a limit set by to avoid excessive API calls
            self.logger.warning(
                f"[get_all_repos] User {user.login} has {user.public_repos} public repos, skipping."
            )
            return None
        try:
            return list(user.get_repos(type="all"))
        except Exception as err:
            self.logger.error(
                f"[get_all_repos] Failed to get repos for user {user.login}: {err}"
            )
            return []

    @ratelimiter
    def get_repo_names(
        self, repos: List[Repository], user: NamedUser | AuthenticatedUser
    ) -> List[str]:
        """
        Get the full names of repositories.

        Args:
            repos (List[Repository]): The list of repositories to extract names from.
            user (NamedUser|AuthenticatedUser): The user to get repository names for.

        Returns:
            List[str]: A list of repository full names.
        """
        try:
            return [repo.full_name for repo in repos]
        except Exception as err:
            self.logger.error(
                f"[get_repo_names] Failed to extract repo names for user {user.login}: {err}"
            )
            return []

    @ratelimiter
    def get_forks_in(
        self, repos: List[Repository]
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the users who forked the specified repositories.

        Args:
            repos (List[Repository]): The list of repositories to get forks for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing forking information.
        """
        forks_in_login = []
        try:
            for repo in repos:
                if not repo.fork:
                    forks_in_login.extend(
                        [
                            {
                                "repo_name": repo.name,
                                "owner_login": fork.owner.login,
                                "created_at": fork.created_at.date().isoformat(),
                            }
                            for fork in repo.get_forks()
                        ]
                    )
            return forks_in_login
        except Exception as err:
            self.logger.error(f"[get_forks_in] Failed on repo {repo.full_name}: {err}")
            return []

    @ratelimiter
    def get_forks_out(
        self, repos: List[Repository], user: NamedUser | AuthenticatedUser
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the users who forked the specified repositories.

        Args:
            repos (List[Repository]): The list of repositories to get forks for.
            user (NamedUser|AuthenticatedUser): The user to get forking information for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing forking information.
        """
        forks_out_login = []
        try:
            for repo in repos:
                if repo.fork:
                    forks_out_login.append(
                        {
                            "repo_name": repo.name,
                            "owner_login": repo.parent.owner.login,
                            "created_at": repo.created_at.date().isoformat(),
                        }
                    )
            return forks_out_login
        except Exception as err:
            self.logger.error(
                f"[get_forks_out] Error accessing fork parent for repo {repo.full_name}, user {user.login}: {err}"
            )
            return []

    @ratelimiter
    def get_stars_in(
        self, repos: List[Repository], user: NamedUser | AuthenticatedUser
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the users who starred the specified repositories.

        Args:
            repos (List[Repository]): The list of repositories to get stars for.
            user (NamedUser|AuthenticatedUser): The user to get starring information for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing starring information.
        """
        stars_in_login = []
        for repo in repos:
            if not repo.fork:
                try:
                    stars = repo.get_stargazers()
                    stars_in_login.extend(
                        [
                            {
                                "repo_name": repo.name,
                                "owner_login": star.login,
                                "created_at": star.created_at.date().isoformat(),
                            }
                            for star in stars
                            if star.login != user.login
                        ]
                    )
                except Exception as err:
                    self.logger.error(
                        f"[get_stars_in] Failed for repo {repo.full_name}, user {user.login}: {err}"
                    )
        return stars_in_login

    @ratelimiter
    def get_stars_out(
        self, user: NamedUser | AuthenticatedUser
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the users who starred the specified repositories.

        Args:
            user (NamedUser|AuthenticatedUser): The user to get starring information for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing starring information.
        """
        try:
            return [
                {
                    "repo_name": repo.name,
                    "owner_login": repo.owner.login,
                    "created_at": repo.created_at.date().isoformat(),
                }
                for repo in user.get_starred()
            ]
        except Exception as err:
            self.logger.error(f"[get_stars_out] Failed for user {user.login}: {err}")
            return []

    @ratelimiter
    def get_watches_in(
        self, repos: List[Repository], user: NamedUser | AuthenticatedUser
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the users who are watching the specified repositories.

        Args:
            repos (List[Repository]): The list of repositories to get watchers for.
            user (NamedUser|AuthenticatedUser): The user to get watching information for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing watching information.
        """
        watch_in_login = []
        for repo in repos:
            try:
                watchers = repo.get_subscribers()
                watch_in_login.extend(
                    {
                        "repo_name": repo.name,
                        "owner_login": watcher.login,
                        "created_at": watcher.created_at.date().isoformat(),
                    }
                    for watcher in watchers
                    if watcher.login != user.login
                )
            except Exception as err:
                self.logger.error(
                    f"[get_watch_in] Failed for repo {repo.full_name}, user {user.login}: {err}"
                )
        return watch_in_login

    @ratelimiter
    def get_watches_out(
        self, user: NamedUser | AuthenticatedUser
    ) -> List[Dict[str, str]] | List[None]:
        """
        Get the users who are watching the specified repositories.

        Args:
            user (NamedUser|AuthenticatedUser): The user to get watching information for.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing watching information.
        """
        try:
            return [
                {
                    "repo_name": repo.name,
                    "owner_login": repo.owner.login,
                    "created_at": repo.created_at.date().isoformat(),
                }
                for repo in user.get_subscriptions()
            ]
        except Exception as err:
            self.logger.error(f"[get_watch_out] Failed for user {user.login}: {err}")
            return []
        
    @ratelimiter
    def get_number_of_public_repos(self, user) -> int:
        """
        Get the number of public repositories for a user.

        Args:
            user (NamedUser|AuthenticatedUser): The user to get information for.

        Returns:
            int: The number of public repositories for the user.
        """
        n_repos = user.public_repos
        return n_repos
    
    def log_user_repo_limit(self, user):
        """
        Add a username to jsonl if the user exceeds the public repository limit.
        """
        # Check if a log file already exist, and if not create it
        log_file = Path("../resources/user_repo_limit_exceeded.jsonl")
        if log_file.exists():
            # Log the user information
            with open(log_file, "a") as f:
                json.dump({"username": user.login}, f)
        else:
            with open(log_file, "w") as f:
                json.dump([{"username": user.login}], f)

    @ratelimiter
    def get_user_info(self, user: NamedUser | AuthenticatedUser, company_label: str, company_filter=True) -> Optional[GithubUser]:
        """
        Get user information for the specified user.

        Args:
            user (NamedUser|AuthenticatedUser): The user to get information for.
            company_label (str): The company label to use for searching.

        Returns:
            GithubUser: An object containing the user's information.
        """
        # 1. Biography columns
        search_with_company = company_label
        user_login = user.login
        usertype = user.type
        company = user.company
        email = user.email
        location = user.location
        bio = user.bio
        blog = user.blog

        # 2. Getting all user's repos
        all_repos = self.get_all_repos(user)

        if all_repos is None:
            return None

        # Check if the user has more than the allowed number of repos
        if all_repos is not None:
            repo_names = self.get_repo_names(all_repos, user)

        # 3. Infer DK location and company match
        ## Filter both on Danish location and company
        if company_filter: 
            match_result = infer_if_dk_and_company(
                user_login=user_login,
                company=company,
                email=email,
                bio=bio,
                blog=blog,
                location=location,
            )
            if match_result is None:
                return None
            location_match, matched_company_strings = match_result

        ## Filter only on Danish location
        elif not company_filter:
            bio_variables = [user_login, company, email, bio, blog]
            bio_variables_clean = [str(bio.lower()) for bio in bio_variables if bio]
            location_result = user_is_from_dk(
                bio_variables=bio_variables_clean,
                user_location=location
            )
            if location_result is None:
                return None
            company_result = search_for_company(
                bio_variables=bio_variables_clean
            )
            location_match = location_result
            matched_company_strings = company_result

        inferred_company = (
            list(matched_company_strings.keys()) if matched_company_strings else None
        )

        # 4. Connections
        follows_in = self.get_follows_in(user)
        follows_out = self.get_follows_out(user)
        watches_in = self.get_watches_in(all_repos, user)
        watches_out = self.get_watches_out(user)
        stars_in = self.get_stars_in(all_repos, user)
        stars_out = self.get_stars_out(user)
        forks_in = self.get_forks_in(all_repos)
        forks_out = self.get_forks_out(all_repos, user)

        # 5. Return the data class
        return GithubUser(
            user_login=user_login,
            search_with_company=search_with_company,
            listed_company=company,
            inferred_company=inferred_company,
            matched_company_strings=matched_company_strings,
            usertype=usertype,
            email=email,
            github_location=location,
            matched_location=location_match,
            bio=bio,
            blog=blog,
            repo_names=repo_names,
            follows_in=follows_in,
            follows_out=follows_out,
            watches_in=watches_in,
            watches_out=watches_out,
            stars_in=stars_in,
            stars_out=stars_out,
            forks_in=forks_in,
            forks_out=forks_out,
        )

    def save_file(
        self, user_row: GithubUser, filename: str, remove_existing_file: bool = False
    ):
        """
        Save user information to a JSONL file.

        Args:
            user_row (GithubUser): The user information to save.
            filename (str): The name of the file to save to.
            remove_existing_file (bool): Whether to remove the existing file before saving.

        Returns:
            None
        """
        filepath = self.output / filename
        if remove_existing_file and filepath.exists():
            filepath.unlink()  # Deletes the existing file
        with open(f"{filepath}.jsonl", "a") as f:
            f.write(json.dumps(asdict(user_row)) + "\n")

    def log_company(self, company: str, log_file_path: str):
        """
        Log company information to a JSONL file.

        Args:
            company (str): The company name to log.
            log_file_path (str): The path to the log file.

        Returns:
            None
        """
        company_dict = {"company_name": company}
        with open(log_file_path, "a") as f:
            f.write(json.dumps(company_dict) + "\n")
        print(f"Company {company} logged.")

    def log_user_w_match(
        self,
        user_login: str,
        inferred_company: str,
        matched_company_strings: dict,
        location_match: str,
        log_file_path: str,
    ):
        """
        Log user match information to a JSONL file.

        Args:
            user_login (str): The user login.
            inferred_company (str): The inferred company name.
            matched_company_strings (dict): The matched company strings.
            location_match (str): The location match.
            log_file_path (str): The path to the log file.

        Returns:
            None
        """
        user_match_dict = {
            "user_login": user_login,
            "inferred_company": inferred_company if inferred_company else None,
            "matched_company_strings": matched_company_strings
            if matched_company_strings
            else None,
            "location_match": location_match if location_match else None,
        }
        GithubScraper.USERS_SCRAPED += 1
        with open(log_file_path, "a") as f:
            f.write(json.dumps(user_match_dict) + "\n")
        print(f"User match {user_login} logged.")

    def log_user_scrape_attempt(self, user_login, log_file_path):
        user_dict = {"user_login": user_login}
        with open(log_file_path, "a") as f:
            f.write(json.dumps(user_dict) + "\n")
        GithubScraper.USERS_ATTEMPTED += 1
