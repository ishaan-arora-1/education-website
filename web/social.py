import logging
import random
import re
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class NitterClient:
    """Client for fetching Twitter/X data via Nitter."""

    # List of Nitter instances to try in case of failure
    NITTER_INSTANCES = [
        "https://nitter.net",
        "https://nitter.privacydev.net",
        "https://nitter.woodland.cafe",
        "https://nitter.mint.lgbt",
        "https://nitter.poast.org",
        "https://nitter.bird.froth.zone",
        "https://nitter.datura.network",
        "https://nitter.edist.ro",
        "https://nitter.tux.pizza",
        "https://nitter.foss.wtf",
        "https://nitter.1d4.us",
        "https://nitter.cz",
        "https://nitter.unixfox.eu",
        "https://nitter.moomoo.me",
        "https://nitter.rawbit.ninja",
        "https://nitter.esmailelbob.xyz",
        "https://nitter.inpt.fr",
        "https://nitter.caioalonso.com",
        "https://nitter.at",
        "https://nitter.nicfab.eu",
    ]

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self, username):
        self.username = username
        self.base_url = None
        self.working_instances = []
        self._find_working_instances()

    def _is_valid_response(self, response_text):
        """Check if the response contains valid profile data."""
        required_elements = [
            'class="profile-card"',
            'class="profile-stat-num"',
            'class="followers"',
            'class="tweet-link"',
        ]
        return all(element in response_text for element in required_elements)

    def _find_working_instances(self):
        """Try all Nitter instances and collect working ones."""
        random.shuffle(self.NITTER_INSTANCES)  # Randomize the order to distribute load

        for instance in self.NITTER_INSTANCES:
            try:
                headers = {
                    "User-Agent": random.choice(self.USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                # First try a basic connection
                response = requests.get(
                    instance,
                    headers=headers,
                    timeout=5,
                    allow_redirects=True,
                )
                response.raise_for_status()

                # If basic connection works, try fetching the actual profile
                profile_response = requests.get(
                    f"{instance}/{self.username}",
                    headers=headers,
                    timeout=10,
                    allow_redirects=True,
                )
                profile_response.raise_for_status()

                if self._is_valid_response(profile_response.text):
                    logger.info(f"Found working Nitter instance: {instance}")
                    self.working_instances.append(instance)
                    if not self.base_url:
                        self.base_url = instance
                else:
                    logger.warning(f"Invalid response from {instance}")

            except requests.RequestException as e:
                logger.warning(f"Failed to connect to Nitter instance {instance}: {str(e)}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error with {instance}: {str(e)}")
                continue

        if not self.working_instances:
            logger.error("No working Nitter instances found")
            logger.error("Tried instances: " + ", ".join(self.NITTER_INSTANCES))

    def get_working_instance(self):
        """Get a working instance, trying to find new ones if necessary."""
        if not self.working_instances:
            self._find_working_instances()

        if self.working_instances:
            self.base_url = random.choice(self.working_instances)
            return self.base_url
        return None

    def get_profile_stats(self):
        """
        Fetch profile statistics from Nitter.
        Returns dict with followers, following, tweets count, and last tweet info.
        """
        if not self.base_url:
            self.base_url = self.get_working_instance()
            if not self.base_url:
                logger.error("No working Nitter instance available")
                return self._get_error_stats("No working Nitter instance available - all instances failed")

        cache_key = f"nitter_stats_{self.username}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                headers = {
                    "User-Agent": random.choice(self.USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                response = requests.get(
                    f"{self.base_url}/{self.username}", headers=headers, timeout=10, allow_redirects=True
                )
                response.raise_for_status()

                if not self._is_valid_response(response.text):
                    # Try another instance if this one returns invalid data
                    if self.base_url in self.working_instances:
                        self.working_instances.remove(self.base_url)
                    self.base_url = self.get_working_instance()
                    if not self.base_url:
                        break
                    retry_count += 1
                    continue

                html_content = response.text

                # Parse profile stats
                stats = self._parse_profile_stats(html_content)

                if not any([stats["followers"], stats["tweets"], stats["last_tweet"]]):
                    logger.warning(f"Failed to parse any meaningful stats for {self.username}")
                    retry_count += 1
                    continue

                # Cache the results for 15 minutes (reduced due to Nitter instability)
                cache.set(cache_key, stats, timeout=900)
                return stats

            except requests.RequestException as e:
                logger.error(f"Error fetching Nitter stats from {self.base_url}: {str(e)}")
                # Try another instance if current one fails
                if self.base_url in self.working_instances:
                    self.working_instances.remove(self.base_url)
                self.base_url = self.get_working_instance()
                if not self.base_url:
                    break
                retry_count += 1

            except Exception as e:
                logger.error(f"Error parsing Nitter stats: {str(e)}")
                retry_count += 1

        return self._get_error_stats("Failed to fetch stats after multiple retries")

    def _parse_profile_stats(self, html_content):
        """Parse the HTML content and extract profile stats."""
        stats = {
            "followers": 0,
            "following": 0,
            "tweets": 0,
            "engagement": 0,
            "last_tweet": None,
            "name": None,
            "bio": None,
            "location": None,
            "website": None,
            "joined": None,
            "error": None,
        }

        # Extract name
        name_pattern = r'class="profile-card-fullname"[^>]*>([^<]+)'
        name_match = re.search(name_pattern, html_content)
        if name_match:
            stats["name"] = name_match.group(1).strip()

        # Extract bio
        bio_pattern = r'class="profile-bio"[^>]*>([^<]+)'
        bio_match = re.search(bio_pattern, html_content)
        if bio_match:
            stats["bio"] = bio_match.group(1).strip()

        # Extract location
        location_pattern = r'class="profile-location"[^>]*>([^<]+)'
        location_match = re.search(location_pattern, html_content)
        if location_match:
            stats["location"] = location_match.group(1).strip()

        # Extract website
        website_pattern = r'class="profile-website"[^>]*href="([^"]+)"'
        website_match = re.search(website_pattern, html_content)
        if website_match:
            stats["website"] = website_match.group(1)

        # Extract joined date
        joined_pattern = r'class="profile-joindate"[^>]*>Joined ([^<]+)'
        joined_match = re.search(joined_pattern, html_content)
        if joined_match:
            try:
                stats["joined"] = datetime.strptime(joined_match.group(1).strip(), "%B %Y")
            except ValueError:
                pass

        # Extract numeric stats using regex
        followers_pattern = r'class="followers"[^>]*>.*?' r'class="profile-stat-num"[^>]*>([^<]+)'
        followers_match = re.search(followers_pattern, html_content, re.DOTALL)
        if followers_match:
            try:
                stats["followers"] = int(followers_match.group(1).strip().replace(",", ""))
            except ValueError:
                pass

        following_pattern = r'class="following"[^>]*>.*?' r'class="profile-stat-num"[^>]*>([^<]+)'
        following_match = re.search(following_pattern, html_content, re.DOTALL)
        if following_match:
            try:
                stats["following"] = int(following_match.group(1).strip().replace(",", ""))
            except ValueError:
                pass

        tweets_pattern = r'class="tweets"[^>]*>.*?' r'class="profile-stat-num"[^>]*>([^<]+)'
        tweets_match = re.search(tweets_pattern, html_content, re.DOTALL)
        if tweets_match:
            try:
                stats["tweets"] = int(tweets_match.group(1).strip().replace(",", ""))
            except ValueError:
                pass

        # Extract latest tweet date
        tweet_date_pattern = r'class="tweet-date"[^>]*>.*?title="([^"]+)"'
        tweet_date_match = re.search(tweet_date_pattern, html_content, re.DOTALL)
        if tweet_date_match:
            try:
                stats["last_tweet"] = datetime.strptime(tweet_date_match.group(1), "%b %d, %Y · %I:%M %p UTC")
            except ValueError:
                pass

        # Calculate engagement rate
        if stats["followers"] > 0 and stats["tweets"] > 0:
            stats["engagement"] = round((stats["tweets"] / stats["followers"]) * 100, 2)

        return stats

    def _get_error_stats(self, error_message):
        """Return stats dict with error message."""
        return {
            "followers": 0,
            "following": 0,
            "tweets": 0,
            "engagement": 0,
            "last_tweet": None,
            "name": None,
            "bio": None,
            "location": None,
            "website": None,
            "joined": None,
            "error": error_message,
        }


def get_social_stats():
    """
    Get stats from all configured social media platforms.
    Returns dict with stats for each platform.
    """
    stats = {}

    # Get X/Twitter stats via Nitter
    if hasattr(settings, "TWITTER_USERNAME"):
        nitter = NitterClient(settings.TWITTER_USERNAME)
        x_stats = nitter.get_profile_stats()
        if x_stats:
            stats["x"] = {
                "stats": x_stats,
                "date": x_stats.get("last_tweet"),
                "status": "danger" if x_stats.get("error") else "success" if x_stats.get("last_tweet") else "neutral",
                "error": x_stats.get("error"),
            }

    # Add other social media platforms here as needed

    return stats
