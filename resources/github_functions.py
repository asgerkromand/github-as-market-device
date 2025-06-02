#######################
### Import Packages ###
#######################

from github import Github
import json
from pathlib import Path
from itertools import cycle
from datetime import datetime
from dataclasses import dataclass, asdict
import time as time
import configparser
import math
import logging
from typing import List, Optional, Dict

config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
config.read(Path(__file__).parent / "config.ini")

# Custom functions
from resources.filter_functions import infer_dk_company_from_values

#############
### Paths ###
#############

fp_main_output = Path(
    '/Volumes/SAM-SODAS-DISTRACT/Coding Distraction/github_as_a_market_device/output'
)


##############
### Tokens ###
##############

### NB! ADD YOUR OWN TOKENS TO YOUR config.ini file, WHICH SHOULD BE STORED IN THE SAME LEVEL AS THIS FILE.
# FOR OUR SCRAPE, 3 TOKENS WERE USED CONTINUALLY.
# ALTERNATIVELY, WITH FEWER TOKENS, SET THE RATE LIMIT ACCORDINGLY ###


# Function to collect GitHub access tokens from config
def collect_github_tokens(
    config: configparser.ConfigParser, section="github", prefix="access_token_"
) -> dict:
    tokens = {}
    i = 1
    while True:
        key = f"{prefix}{i}"
        try:
            token = config.get(section, key)
            tokens[f"ACCESS_TOKEN_{i}"] = token
            i += 1
        except (configparser.NoOptionError, configparser.NoSectionError):
            break
    return tokens

# Collect GitHub access tokens from the config file
github_access_tokens = collect_github_tokens(config)

#######################################################
### Custom Made Functions For Scraping Github Users ###
#######################################################

# Ratelimiter decorator
def ratelimiter(func):
    def wrapper(*args, **kwargs):
        github_scraper = args[0]  # [0] is the 'self' argument from the class

        # Working with different rate-limits
        max_rate = github_scraper.github.rate_limiting[1]
        if max_rate == 30:
            ratelimit = 5
            # print(f'Setting the ratelimit to {ratelimit}')
        elif max_rate == 5000:
            ratelimit = 300
            # print(f'Setting the ratelimit to {ratelimit}')
        else:
            # print(f'Max rate was unknown: {max_rate}.')
            ratelimit = 200

        if github_scraper.github.rate_limiting[0] < ratelimit:
            if github_scraper._max_n_cycle > github_scraper._n_iter:
                github_scraper._cycle_github()
                github_scraper._n_iter = +1
                print("Cycle")
            else:
                print(
                    f"There has been cycled {github_scraper._n_iter} time(s) out of a max of {github_scraper._max_n_cycle} time(s)"
                )
                time_before_reset = (
                    github_scraper.github.rate_limiting_resettime - time.time()
                )  # calculating time before reset
                print(
                    f"Waiting {time_before_reset} seconds (or {round(time_before_reset/60, 2)} mins) for reseting of rates"
                )
                time.sleep(time_before_reset + 10)  # adding 10 seconds to be sure
        result = func(*args, **kwargs)
        return result

    return wrapper

# Dataclass
@dataclass
class GithubUser:
    user_login: str | None
    search_with_company: str | None
    listed_company: str | None
    inferred_company: Optional[List[str]]  
    matched_company_strings: Optional[Dict[str, List[str]]]
    usertype: str | None
    email: str | None
    location: str | list[str] | None
    bio: str | None
    blog: str | None
    repo_names: list[str] | None
    follows_in: list[str] | None
    follows_out: list[str] | None
    watches_in: list[str] | None
    watches_out: list[str] | None
    stars_in: list[str] | None
    stars_out: list[str] | None
    forks_in: list[str] | None
    forks_out: list[str] | None
    

class GithubScraper:
    USERS_ATTEMPTED = 0
    USERS_SCRAPED = 0
    COMPANIES_SCRAPED = 0

    def __init__(
        self,
        tokens: dict[str, str] = github_access_tokens,
        repo_limit: int = 50,
        users_already_attempted: set[str] | None = None,
        users_already_scraped: set[str] | None = None,
        companies_already_scraped: set[str] | None = None,
        output: Path = fp_main_output,
    ):
        self.access_tokens = tokens
        print(f"GithubScraper initialized with {len(self.access_tokens)} tokens.")
        self.token_cycle = cycle(self.access_tokens)
        self._n_iter = 0
        self._max_n_cycle = len(tokens)
        self._cycle_github()
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

    def _cycle_github(self):
        self._n_iter += 1
        self.current_token_key = next(
            self.token_cycle
        )  # Get the next token key (e.g., "ACCESS_TOKEN_1")
        self.current_token_value = self.access_tokens[
            self.current_token_key
        ]  # Get the actual token value
        self.github = Github(
            self.current_token_value
        )  # Authenticate with the new token
        if self._n_iter == 1:
            print(f"First token in cycle. Initiating {self.current_token_key}.")
        else:
            print(f"Token cycled to {self.current_token_key}.")

    def setup_logging(self):
        """Setup the logging configuration (file-only, silent in terminal)."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.log_dir = self.output / "log"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.log_dir / f"scrape_log_github_{time.strftime('%Y%m%d_%H%M%S')}.log"
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
    def get_gh_users(self, company_query, no_location_filter_bool):
        filter_string = self.filter_string
        if no_location_filter_bool == 1:
            users = [
                (user_gh, company_query)
                for user_gh in [
                    *self.github.search_users(company_query)
                ]
            ]
        elif no_location_filter_bool == 0:
            company_query = f"{company_query} {filter_string}"
            users = [
                (user_gh, company_query)
                for user_gh in [
                    *self.github.search_users(company_query)
                ]
            ]
        if len([*users]) > 0:
            return users
        else:
            print(no_location_filter_bool, "- no users found")
            return users
        
    @ratelimiter
    def get_user(self, user_login):
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
    def get_follows_in(self, user):
        follows_in = []
        try:
            follows_in.extend(
                [
                    {
                        'repo_name': None,
                        'owner_login': follower.login,
                        'created_at': follower.created_at.date().isoformat(),
                    }
                    for follower in user.get_followers()
                ]
            )
            return follows_in
        except Exception as err:
            self.logger.error(f"[get_follow_in] Failed to get followers for user {user.login}: {err}")
            return []
    
    @ratelimiter
    def get_follows_out(self, user):
        follows_out = []
        try:
            follows_out.extend(
                [
                    {
                        'repo_name': None,
                        'owner_login': follower.login,
                        'created_at': follower.created_at.date().isoformat(),
                    }
                    for follower in user.get_following()
                ]
            )
            return follows_out
        except Exception as err:
            self.logger.error(f"[get_follow_out] Failed to get following for user {user.login}: {err}")
            return []
    
    @ratelimiter
    def get_all_repos(self, user):
        if user.public_repos > self.repo_limit: #IMPORTANT methodological choice: This is a limit set by us to avoid excessive API calls
            self.logger.warning(f"[get_all_repos] User {user.login} has {user.public_repos} public repos, skipping.")
            return None
        try:
            return list(user.get_repos(type="all"))
        except Exception as err:
            self.logger.error(f"[get_all_repos] Failed to get repos for user {user.login}: {err}")
            return []
    
    @ratelimiter
    def get_repo_names(self, repos, user):
        try:
            return [repo.full_name for repo in repos]
        except Exception as err:
            self.logger.error(f"[get_repo_names] Failed to extract repo names for user {user.login}: {err}")
            return []
    
    @ratelimiter
    def get_forks_in(self, repos):
        forks_in_login = []
        try:
            for repo in repos:
                if not repo.fork:
                    forks_in_login.extend(
                        [
                            {
                                'repo_name': repo.name,
                            'owner_login': fork.owner.login,
                            'created_at': fork.created_at.date().isoformat(),
                            }
                    for fork in repo.get_forks()
                    ])
            return forks_in_login
        except Exception as err:
            self.logger.error(f"[get_forks_in] Failed on repo {repo.full_name}: {err}")
            return []
    
    @ratelimiter
    def get_forks_out(self, repos, user):
        forks_out_login = []
        try:
            for repo in repos:
                if repo.fork:
                    forks_out_login.append(
                        {
                            'repo_name': repo.name,
                            'owner_login': repo.parent.owner.login,
                            'created_at': repo.created_at.date().isoformat(),
                        }
                    )
            return forks_out_login
        except Exception as err:
            self.logger.error(f"[get_forks_out] Error accessing fork parent for repo {repo.full_name}, user {user.login}: {err}")
            return []
    
    @ratelimiter
    def get_stars_in(self, repos, user):
        stars_in_login = []
        for repo in repos:
            if not repo.fork:
                try:
                    stars = repo.get_stargazers()
                    stars_in_login.extend([
                        {
                            'repo_name': repo.name,
                            'owner_login': star.login,
                            'created_at': star.created_at.date().isoformat(),
                        }
                        for star in stars if star.login != user.login
                    ]
                    )
                except Exception as err:
                    self.logger.error(f"[get_stars_in] Failed for repo {repo.full_name}, user {user.login}: {err}")
        return stars_in_login
    
    @ratelimiter
    def get_stars_out(self, user):
        try:
            return [{
                'repo_name': repo.name,
                'owner_login': repo.owner.login,
                'created_at': repo.created_at.date().isoformat(),
                }
                for repo in user.get_starred()]
        except Exception as err:
            self.logger.error(f"[get_stars_out] Failed for user {user.login}: {err}")
            return []
    
    @ratelimiter
    def get_watches_in(self, repos, user):
        watch_in_login = []
        for repo in repos:
            try:
                watchers = repo.get_subscribers()
                watch_in_login.extend({
                    'repo_name': repo.name,
                    'owner_login': watcher.login,
                    'created_at': watcher.created_at.date().isoformat(),
                }
                for watcher in watchers if watcher.login != user.login)
            except Exception as err:
                self.logger.error(f"[get_watch_in] Failed for repo {repo.full_name}, user {user.login}: {err}")
        return watch_in_login
    
    @ratelimiter
    def get_watches_out(self, user):
        try:
            return [{
                'repo_name': repo.name,
                'owner_login': repo.owner.login,
                'created_at': repo.created_at.date().isoformat(),
            }
            for repo in user.get_subscriptions()]
        except Exception as err:
            self.logger.error(f"[get_watch_out] Failed for user {user.login}: {err}")
            return []
    
    @ratelimiter
    def get_user_info(self, user, company_label):
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
            print(f"User {user_login} has more than {self.repo_limit} repos, skipping.")
            return None
        repo_names = self.get_repo_names(all_repos, user)

        # 3. Infer DK location and company match
        match_result = infer_dk_company_from_values(
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
        inferred_company = list(matched_company_strings.keys()) if matched_company_strings else None

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
            location=location_match,
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

    def save_file(self, user_row, filename, remove_existing_file=False):
        filepath = self.output / filename
        if remove_existing_file and filepath.exists():
            filepath.unlink()  # Deletes the existing file
        with open(f"{filepath}.jsonl", "a") as f:
            f.write(json.dumps(asdict(user_row)) + "\n")

    def log_company(self, company, log_file_path):
        company_dict = {"company_name": company}
        with open(log_file_path, "a") as f:
            f.write(json.dumps(company_dict) + "\n")
        print(f"Company {company} logged.")

    def log_user_w_match(self, user_login, inferred_company, matched_company_strings, location_match, log_file_path):
        user_match_dict = {
            "user_login": user_login,
            "inferred_company": inferred_company if inferred_company else None,
            "matched_company_strings": matched_company_strings if matched_company_strings else None,
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
