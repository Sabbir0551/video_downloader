/**
 * Client-side fast platform detector for immediate URL input feedback.
 */

export interface QuickPlatformInfo {
  id: string;
  name: string;
  tier: "supported" | "best_effort" | "unsupported_no_video" | "login_or_paid" | "defunct";
  warningBn?: string;
  warningEn?: string;
}

const DOMAIN_MAP: Record<string, QuickPlatformInfo> = {
  // Supported
  "youtube.com": { id: "youtube", name: "YouTube", tier: "supported" },
  "youtu.be": { id: "youtube", name: "YouTube", tier: "supported" },
  "facebook.com": { id: "facebook", name: "Facebook", tier: "supported" },
  "fb.watch": { id: "facebook", name: "Facebook", tier: "supported" },
  "instagram.com": { id: "instagram", name: "Instagram", tier: "supported" },
  "tiktok.com": { id: "tiktok", name: "TikTok", tier: "supported" },
  "x.com": { id: "twitter", name: "X (Twitter)", tier: "supported" },
  "twitter.com": { id: "twitter", name: "X (Twitter)", tier: "supported" },
  "reddit.com": { id: "reddit", name: "Reddit", tier: "supported" },
  "v.redd.it": { id: "reddit", name: "Reddit", tier: "supported" },
  "vimeo.com": { id: "vimeo", name: "Vimeo", tier: "supported" },
  "twitch.tv": { id: "twitch", name: "Twitch", tier: "supported" },
  "soundcloud.com": { id: "soundcloud", name: "SoundCloud", tier: "supported" },
  "bilibili.com": { id: "bilibili", name: "Bilibili", tier: "supported" },
  "threads.net": { id: "threads", name: "Threads", tier: "supported" },
  "dailymotion.com": { id: "dailymotion", name: "Dailymotion", tier: "supported" },
  "dai.ly": { id: "dailymotion", name: "Dailymotion", tier: "supported" },
  "pinterest.com": { id: "pinterest", name: "Pinterest", tier: "supported" },
  "pin.it": { id: "pinterest", name: "Pinterest", tier: "supported" },
  "vk.com": { id: "vk", name: "VK", tier: "supported" },
  "ok.ru": { id: "ok_ru", name: "Odnoklassniki", tier: "supported" },

  // Best effort
  "telegram.org": { id: "telegram", name: "Telegram", tier: "best_effort" },
  "t.me": { id: "telegram", name: "Telegram", tier: "best_effort" },
  "bluesky.app": { id: "bluesky", name: "Bluesky", tier: "best_effort" },
  "bsky.app": { id: "bluesky", name: "Bluesky", tier: "best_effort" },
  "mastodon.social": { id: "mastodon", name: "Mastodon", tier: "best_effort" },

  // Unsupported (Messaging / Chat / Dating / Forum without video)
  "whatsapp.com": {
    id: "whatsapp",
    name: "WhatsApp",
    tier: "unsupported_no_video",
    warningBn: "হোয়াটসঅ্যাপ একটি এন্ড-টু-এন্ড এনক্রিপ্টেড প্রাইভেট মেসেজিং অ্যাপ। এতে কোনো পাবলিক ভিডিও কনটেন্ট নেই।",
    warningEn: "WhatsApp is an encrypted private messaging app. It does not host public videos.",
  },
  "wechat.com": {
    id: "wechat",
    name: "WeChat",
    tier: "unsupported_no_video",
    warningBn: "উইচ্যাট একটি প্রাইভেট মেসেজিং অ্যাপ। এর ভিডিও পাবলিকলি ডাউনলোডযোগ্য নয়।",
    warningEn: "WeChat is a closed private network and cannot be downloaded publicly.",
  },
  "tinder.com": {
    id: "tinder",
    name: "Tinder",
    tier: "unsupported_no_video",
    warningBn: "টিন্ডার একটি প্রাইভেট ডেটিং অ্যাপ। এতে কোনো পাবলিক ভিডিও নেই।",
    warningEn: "Tinder is a private dating application without public video hosting.",
  },
  "bumble.com": {
    id: "bumble",
    name: "Bumble",
    tier: "unsupported_no_video",
    warningBn: "বাম্বল একটি প্রাইভেট ডেটিং অ্যাপ। এর প্রোফাইল পাবলিক নয়।",
    warningEn: "Bumble profiles are private.",
  },
  "quora.com": {
    id: "quora",
    name: "Quora",
    tier: "unsupported_no_video",
    warningBn: "কোরা একটি প্রশ্ন-উত্তর সাইট। এতে নিজস্ব পাবলিক ভিডিও হোস্ট করা হয় না।",
    warningEn: "Quora is a Q&A platform without standalone public video files.",
  },
  "news.ycombinator.com": {
    id: "hackernews",
    name: "Hacker News",
    tier: "unsupported_no_video",
    warningBn: "হ্যাকার নিউজ টেক্সট ও লিংক ফোরাম। এতে ভিডিও কনটেন্ট নেই।",
    warningEn: "Hacker News is a text/discussion board without video hosting.",
  },

  // Login / Paywalled
  "onlyfans.com": {
    id: "onlyfans",
    name: "OnlyFans",
    tier: "login_or_paid",
    warningBn: "অনলিফ্যানস একটি পেইড সাবস্ক্রিপশন প্ল্যাটফর্ম। কপিরাইট ও পলিসি অনুযায়ী এটি সমর্থিত নয়।",
    warningEn: "OnlyFans is a paid subscription service and is blocked by policy.",
  },
  "patreon.com": {
    id: "patreon",
    name: "Patreon",
    tier: "login_or_paid",
    warningBn: "প্যাট্রিয়ন পেইড মেম্বারশিপ কনটেন্ট। এটি ডাউনলোড করা যাবে না।",
    warningEn: "Patreon requires paid subscription credentials.",
  },

  // Defunct
  "kooapp.com": {
    id: "koo",
    name: "Koo",
    tier: "defunct",
    warningBn: "কু (Koo) ২০২৪ সালের জুলাইয়ে স্থায়ীভাবে বন্ধ হয়ে গেছে।",
    warningEn: "Koo permanently shut down operations in July 2024.",
  },
};

export function detectQuickPlatform(rawUrl: string): QuickPlatformInfo | null {
  try {
    const parsed = new URL(rawUrl.trim());
    const host = parsed.hostname.toLowerCase().replace(/^www\./, "");
    if (DOMAIN_MAP[host]) return DOMAIN_MAP[host];

    // Check parent domains
    for (const [dom, info] of Object.entries(DOMAIN_MAP)) {
      if (host.endsWith(`.${dom}`)) {
        return info;
      }
    }
  } catch {
    return null;
  }
  return null;
}

