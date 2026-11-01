# AnyStream Platform Support Matrix (100 Platforms)

> **Last Verified:** 2026-11-01 | **yt-dlp Version:** `2026.10.26` | **Total Scoped:** 100

## Tier Breakdown Summary

| Tier | Count | Description | Action Policy |
| :--- | :---: | :--- | :--- |
| `supported` | **38** | Dedicated extractor with public video & audio | Direct high-speed download up to 4K/1080p |
| `best_effort` | **21** | Generic/embed or direct media extraction | Best-effort resolution without login |
| `unsupported_no_video` | **29** | Messaging, dating, Q&A/dev forums without video | Early refusal in UI before hitting backend |
| `login_or_paid` | **9** | Paywalled, subscription, adult, or login-gated | Immediate refusal with honest localized explanation |
| `defunct` | **3** | Shut down / liquidated platforms (e.g. Koo, Ello) | Immediate refusal with service discontinuation note |

## Honest Policy & Scope Enforcement
1. **Public Content Only**: AnyStream strictly does not circumvent paywalls, bypass authentication walls, or download private end-to-end encrypted chats.
2. **Early Gating**: Non-video, login-gated, and defunct domains are caught client-side and at API admission, saving upstream server compute and proxy bandwidth.
3. **DMCA Compliance**: Administrative takedowns instantly invalidate URLs and canonical video IDs across all tiers.

## Platform Inventory Table

| # | Platform | Tier | Category | Max Quality | Extractor(s) | Notes |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- |
| 1 | **Facebook** | `supported` | social | 1080p | `Facebook`, `FacebookPlugins`, `FacebookReel` | Supports public posts, reels, and watch videos. Private groups or friends-only posts require login and are not supported. |
| 2 | **YouTube** | `supported` | video_audio | 4k | `Youtube`, `YoutubeTab`, `YoutubeShorts`, `YoutubeClip` | Full support for standard videos, Shorts, and audio extraction up to 4K/8K. Members-only or age-gated videos requiring login are refused. |
| 3 | **WhatsApp** | `unsupported_no_video` | messaging | none | — | Private end-to-end encrypted messaging service. No public video hosting. |
| 4 | **Instagram** | `supported` | social | 1080p | `Instagram`, `InstagramStory` | Supports public reels, posts, and IGTV. Private profiles and expired stories require login and are not supported. |
| 5 | **TikTok** | `supported` | video_audio | 1080p | `TikTok`, `TikTokUser` | Watermark-free original video stream extraction supported where provided by upstream CDN. |
| 6 | **WeChat** | `unsupported_no_video` | messaging | none | — | Private messaging and closed ecosystem. Channels/Moments require internal WeChat app authentication. |
| 7 | **Messenger** | `unsupported_no_video` | messaging | none | — | Private 1-on-1 and group messaging platform. No public standalone video URLs. |
| 8 | **Telegram** | `best_effort` | messaging | 720p | `telegram:embed` | Supports public channel video embeds via t.me/channel/msg_id. Private chat files require MTProto login and are refused. |
| 9 | **Snapchat** | `supported` | social | 720p | `Snapchat` | Public Spotlight and public Story links supported. Ephemeral private snaps cannot be retrieved. |
| 10 | **Douyin** | `supported` | video_audio | 1080p | `Douyin` | Chinese domestic TikTok counterpart. Public video links supported without watermark. |
| 11 | **Kuaishou** | `supported` | video_audio | 1080p | `Kwai` | Short video platform. Public Kwai/Kuaishou shares supported. |
| 12 | **Sina Weibo** | `supported` | social | 1080p | `Weibo` | Public video status posts supported via dedicated Weibo extractor. |
| 13 | **QQ** | `unsupported_no_video` | messaging | none | — | Instant messaging app. (QQMusic is a distinct music service, QQ itself has no public video). |
| 14 | **X (Twitter)** | `supported` | social | 1080p | `Twitter` | Public tweets with native video/GIF. Multi-video tweets extract the primary video stream. |
| 15 | **Pinterest** | `supported` | photo_art | 720p | `PinterestCollection`, `Pinterest` | Supports video pins and story pins. |
| 16 | **Reddit** | `supported` | community_forum | 1080p | `Reddit` | Merges v.redd.it DASH video and DASH audio streams into unified output. |
| 17 | **LinkedIn** | `supported` | professional | 1080p | `linkedin:events`, `LinkedIn`, `linkedin:learning:course`, `linkedin:learning` | Public video feed posts supported. Private company pages or gated feeds require login. |
| 18 | **Threads** | `supported` | social | 1080p | `Threads` | Public video posts supported via Instagram/Threads GraphQL extractor. |
| 19 | **Quora** | `unsupported_no_video` | community_forum | none | — | Text and image Q&A platform. Does not host standalone public video files. |
| 20 | **Discord** | `best_effort` | community_forum | 1080p | — | Direct media URLs (cdn.discordapp.com) supported. Channel messages require bot authorization. |
| 21 | **Tumblr** | `supported` | creator_writing | 720p | `Tumblr` | Public video blog posts supported. |
| 22 | **Twitch** | `supported` | video_audio | 1080p | `TwitchVod`, `TwitchClips` | Supports public Clips and recorded VODs. Ongoing live streams are not permitted for static download. |
| 23 | **VK (VKontakte)** | `supported` | social | 1080p | `VK` | Public VK wall and VK Video clips supported. |
| 24 | **Line** | `best_effort` | messaging | 720p | — | Line VOOM public video posts supported via generic/embed; 1-on-1 chats are private. |
| 25 | **Viber** | `unsupported_no_video` | messaging | none | — | Private messaging app. No public video hosting. |
| 26 | **Signal** | `unsupported_no_video` | messaging | none | — | End-to-end encrypted private messaging. Zero public video hosting. |
| 27 | **Bluesky** | `supported` | social | 720p | `Bluesky` | Public video posts (HLS/video.bsky.app) supported. |
| 28 | **Mastodon** | `supported` | social | 1080p | `Mastodon` | Decentralized ActivityPub federation. Public video attachments supported. |
| 29 | **KakaoTalk** | `unsupported_no_video` | messaging | none | `Kakao` | Closed Korean mobile messaging network. No public video hosting. |
| 30 | **Zalo** | `unsupported_no_video` | messaging | none | — | Vietnamese messaging service. Chats are private. |
| 31 | **Odnoklassniki (OK)** | `supported` | social | 1080p | `Odnoklassniki` | Russian social network with extensive public video hosting. Dedicated Odnoklassniki extractor. |
| 32 | **Bilibili** | `supported` | video_audio | 1080p | `BiliBili` | Multi-part videos supported (defaults to part 1). VIP-only 4K requires login and is refused. |
| 33 | **Xiaohongshu (RedNote)** | `best_effort` | social | 1080p | `XiaoHongShu` | Public video notes extractable via og:video and web API. |
| 34 | **Zhihu** | `supported` | community_forum | 720p | `Zhihu` | Chinese Q&A site with video answers. Zhihu extractor available for public video answers. |
| 35 | **Douban** | `best_effort` | community_forum | 720p | — | Public trailers and clip reviews extractable via generic extractor. |
| 36 | **Likee** | `supported` | video_audio | 1080p | `likee`, `likee:user` | Short video platform. Dedicated Likee extractor supported. |
| 37 | **Bigo Live** | `supported` | video_audio | 720p | `Bigo` | Recorded public video clips supported via Bigo extractor. Live streams excluded. |
| 38 | **Kik** | `unsupported_no_video` | messaging | none | — | Anonymous mobile messaging app. (Kika extractor is an unrelated German TV site). |
| 39 | **Flickr** | `supported` | photo_art | 1080p | `Flickr` | Public video photos supported via Flickr extractor. |
| 40 | **Medium** | `best_effort` | creator_writing | 720p | — | Articles occasionally embed third-party public videos. |
| 41 | **Clubhouse** | `unsupported_no_video` | community_forum | none | — | Live voice rooms without public standalone video hosting. |
| 42 | **Nextdoor** | `login_or_paid` | social | none | — | Neighborhood network strictly gated by private address verification and login. |
| 43 | **Vimeo** | `supported` | video_audio | 4k | `Vimeo` | Full support for public videos and on-demand content up to 4K. Password-protected videos refused. |
| 44 | **SoundCloud** | `supported` | video_audio | none | `Soundcloud` | Audio platform. Extracts original 128-256kbps MP3/Opus/AAC audio streams. |
| 45 | **Goodreads** | `unsupported_no_video` | community_forum | none | — | Book reviews and reading catalog. No public video hosting. |
| 46 | **Behance** | `best_effort` | photo_art | 1080p | — | Portfolio projects containing public MP4/WebM video embeds supported via generic extractor. |
| 47 | **Dribbble** | `supported` | photo_art | 1080p | — | Public video shots supported via Dribbble extractor. |
| 48 | **DeviantArt** | `supported` | photo_art | 1080p | — | Public video art and animations supported via DeviantArt extractor. |
| 49 | **ArtStation** | `supported` | photo_art | 1080p | — | Digital art portfolios. Public project video clips supported via ArtStation extractor. |
| 50 | **500px** | `unsupported_no_video` | photo_art | none | — | Still photography platform only. No public video hosting. |
| 51 | **GitHub** | `best_effort` | professional | 1080p | — | Public repository release assets and user-uploaded issue/PR demo videos supported via direct URL. |
| 52 | **GitLab** | `best_effort` | professional | 1080p | — | Public release assets and snippet videos supported via generic extractor. |
| 53 | **Stack Overflow** | `unsupported_no_video` | professional | none | — | Developer Q&A site. No native video hosting. |
| 54 | **Dev.to** | `best_effort` | professional | 720p | — | Developer blogging platform with third-party video embeds. |
| 55 | **Hashnode** | `best_effort` | professional | 720p | — | Developer blogging platform with embedded public videos. |
| 56 | **Product Hunt** | `best_effort` | professional | 1080p | — | Product demo videos and gallery clips supported via generic extractor. |
| 57 | **Kaggle** | `unsupported_no_video` | professional | none | — | Data science datasets and notebooks. No public video hosting. |
| 58 | **Polywork** | `unsupported_no_video` | professional | none | — | Professional networking portfolio. No public video hosting. |
| 59 | **Mastodon Fediverse** | `supported` | social | 1080p | — | Federated ActivityPub video posts. |
| 60 | **MeWe** | `login_or_paid` | social | none | — | Private social network requiring account login for all member posts. |
| 61 | **ShareChat** | `supported` | social | 720p | `ShareChat` | Indian regional social network with public videos supported via dedicated extractor. |
| 62 | **Moj** | `supported` | video_audio | 1080p | `Moj` | Indian short video app (ShareChat subsidiary). Public video links supported. |
| 63 | **Koo** | `defunct` | social | none | — | Defunct service. Koo permanently shut down all operations in July 2024. |
| 64 | **Skype** | `unsupported_no_video` | messaging | none | — | VoIP and teleconferencing service. No public video hosting. |
| 65 | **imo** | `unsupported_no_video` | messaging | none | — | Private mobile video calling and chat app. No public video sharing. |
| 66 | **Tinder** | `unsupported_no_video` | dating | none | — | Private dating application. Gated behind phone login. No public video URLs. |
| 67 | **Bumble** | `unsupported_no_video` | dating | none | — | Dating and professional networking app. Closed user profiles only. |
| 68 | **Hinge** | `unsupported_no_video` | dating | none | — | Private dating app. No public web profiles or video hosting. |
| 69 | **Badoo** | `unsupported_no_video` | dating | none | — | Dating network. Profiles require authentication. |
| 70 | **Tagged** | `login_or_paid` | social | none | — | Social discovery site requiring login to view live streams or user content. |
| 71 | **Hi5** | `login_or_paid` | social | none | — | Social discovery website requiring login to access media. |
| 72 | **Ask.fm** | `best_effort` | community_forum | 720p | — | Public video answers extractable via direct media links. |
| 73 | **Weverse** | `login_or_paid` | community_forum | none | `Weverse`, `WeverseLive`, `WeverseLiveTab`, `WeverseMedia`, `WeverseMediaTab`, `WeverseMoment` | K-pop fan community. Media is DRM-protected and gated behind user login. |
| 74 | **Naver Band** | `best_effort` | community_forum | 720p | — | Public community band video posts supported; private bands require login. |
| 75 | **Cyworld** | `defunct` | social | none | — | Defunct Korean retro social network. Service has suspended web operations. |
| 76 | **Mixi** | `login_or_paid` | social | none | — | Japanese private community network requiring SMS verification and login. |
| 77 | **Ameba** | `best_effort` | creator_writing | 720p | — | Japanese blogging network. Public blog video posts supported. |
| 78 | **Niconico** | `supported` | video_audio | 1080p | `NicoNico` | Japanese video platform. Dedicated Niconico extractor supported. Premium-only videos refused. |
| 79 | **Plurk** | `best_effort` | social | 720p | — | Taiwanese microblogging service. Public timeline video links supported. |
| 80 | **Gaia Online** | `unsupported_no_video` | community_forum | none | — | Anime forum and virtual avatar community. No standalone video hosting. |
| 81 | **Pixiv** | `supported` | photo_art | 1080p | — | Japanese artwork community. Ugoira (animated art) extraction supported via Pixiv extractor. |
| 82 | **Wattpad** | `unsupported_no_video` | creator_writing | none | — | Story and novel reading platform. No standalone public video hosting. |
| 83 | **Substack** | `best_effort` | creator_writing | 1080p | `Substack` | Public video podcasts and posts supported. Paid subscriber newsletters are refused. |
| 84 | **Patreon** | `login_or_paid` | creator_writing | none | `patreon:campaign`, `patreon` | Subscription paywall platform. Commercial creator content is strictly protected. |
| 85 | **OnlyFans** | `login_or_paid` | creator_writing | none | — | Strictly paywalled, DRM-protected, adult subscription service. Downloads prohibited by policy. |
| 86 | **Ko-fi** | `best_effort` | creator_writing | 720p | — | Public gallery video updates supported. Supporter-only tiers are refused. |
| 87 | **Mix** | `unsupported_no_video` | community_forum | none | — | Content discovery bookmarking tool (formerly StumbleUpon). (Mixcloud is a separate audio site). |
| 88 | **Diaspora*** | `best_effort` | social | 720p | — | Decentralized social web pod posts. |
| 89 | **Minds** | `supported` | social | 1080p | `minds:channel`, `minds:group`, `minds` | Open-source social network. Public video posts supported via Minds extractor. |
| 90 | **Ello** | `defunct` | photo_art | none | — | Defunct art network. Ello announced complete shutdown and domain liquidation. |
| 91 | **Vero** | `best_effort` | social | 1080p | — | Public web share links supported via generic extractor. |
| 92 | **BeReal** | `unsupported_no_video` | social | none | — | Daily dual-camera photo sharing app. Gated in-app experience without public video. |
| 93 | **Lemon8** | `supported` | social | 1080p | `Lemon8` | ByteDance lifestyle and video app. Dedicated Lemon8 extractor supported. |
| 94 | **Triller** | `supported` | video_audio | 1080p | `Triller` | Short-form music video platform. Dedicated Triller extractor supported. |
| 95 | **Dailymotion** | `supported` | video_audio | 1080p | `Dailymotion` | Major video sharing platform. Dedicated Dailymotion extractor with multi-resolution support. |
| 96 | **Lobsters** | `unsupported_no_video` | community_forum | none | — | Tech link aggregation and discussion. No video hosting. |
| 97 | **Hacker News** | `unsupported_no_video` | community_forum | none | — | Y Combinator discussion board. Pure text/links only. |
| 98 | **Slack** | `login_or_paid` | messaging | none | — | Enterprise workplace messaging. Gated behind workspace credentials. |
| 99 | **Element (Matrix)** | `unsupported_no_video` | messaging | none | — | Decentralized encrypted communication protocol. Rooms are private/invitation-based. |
| 100 | **Pillowfort** | `best_effort` | social | 720p | — | Community blogging platform. Public media posts extractable. |

---
*Generated automatically from `backend/app/platforms/registry.yaml`.*