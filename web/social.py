from datetime import datetime

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache


class NitterClient:
    """Client for fetching Twitter/X data via Nitter."""

    def __init__(self, username):
        self.username = username
        self.base_url = "https://nitter.net"

    def get_profile_stats(self):
        """
        Fetch profile statistics from Nitter.
        Returns dict with followers, following, tweets count, and last tweet info.
        """
        cache_key = f"nitter_stats_{self.username}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            response = requests.get(
                f"{self.base_url}/{self.username}", headers={"User-Agent": "Mozilla/5.0"}, timeout=10
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Parse profile stats
            stats = {}
            stats_div = soup.find("div", class_="profile-stats")
            if stats_div:
                # Get followers count
                followers_elem = stats_div.find("li", class_="followers")
                if followers_elem:
                    followers_text = followers_elem.find("span", class_="profile-stat-num").text.strip()
                    stats["followers"] = int(followers_text.replace(",", ""))

                # Get tweets count
                tweets_elem = stats_div.find("li", class_="tweets")
                if tweets_elem:
                    tweets_text = tweets_elem.find("span", class_="profile-stat-num").text.strip()
                    stats["tweets"] = int(tweets_text.replace(",", ""))

            # Get latest tweet
            timeline = soup.find("div", class_="timeline")
            if timeline:
                latest_tweet = timeline.find("div", class_="tweet-date")
                if latest_tweet:
                    tweet_link = latest_tweet.find("a")
                    if tweet_link:
                        tweet_date = tweet_link.get("title")
                        if tweet_date:
                            stats["last_tweet"] = datetime.strptime(tweet_date, "%b %d, %Y · %I:%M %p UTC")

            # Calculate engagement rate (simplified)
            if "followers" in stats and "tweets" in stats and stats["followers"] > 0:
                stats["engagement"] = round((stats["tweets"] / stats["followers"]) * 100, 2)
            else:
                stats["engagement"] = 0

            # Cache the results for 1 hour
            cache.set(cache_key, stats, timeout=3600)

            return stats

        except Exception as e:
            print(f"Error fetching Nitter stats: {str(e)}")
            return {"followers": 0, "tweets": 0, "engagement": 0, "last_tweet": None}


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
                "status": "success" if x_stats.get("last_tweet") else "neutral",
            }

    # Add other social media platforms here as needed

    return stats
