export type Language = "en" | "bn";

export interface Translations {
  appName: string;
  tagline: string;
  urlPlaceholder: string;
  paste: string;
  clear: string;
  search: string;
  searching: string;
  emptyUrlError: string;
  invalidUrlError: string;
  supportedPlatforms: string;
  apiOnline: string;
  apiOffline: string;
  apiConnecting: string;
  changeQualityOrUrl: string;
  qualitySectionTitle: string;
  tabVideo: string;
  tabAudio: string;
  selectedQuality: string;
  bestQuality: string;
  bestQualityDesc: string;
  optimalQuality: string;
  estSizeAuto: string;
  audioOnly: string;
  mp3Title: string;
  mp3Desc: string;
  universalCompatible: string;
  m4aTitle: string;
  m4aDesc: string;
  directAacStream: string;
  resolution: string;
  format: string;
  estSize: string;
  downloadNow: string;
  starting: string;
  queued: string;
  processing: string;
  merging: string;
  completed: string;
  failed: string;
  cancelled: string;
  cancel: string;
  cancelling: string;
  retry: string;
  saveFile: string;
  speed: string;
  eta: string;
  timeLeft: string;
  seconds: string;
  secureTokenVerified: string;
  linkExpiresIn30Mins: string;
  legalNotice: string;
  legalDisclaimer: string;
  historyTitle: string;
  noHistory: string;
  clearHistory: string;
  close: string;
  themeLight: string;
  themeDark: string;
  terms: string;
  privacy: string;
  dmca: string;
  footerRights: string;
  errors: Record<string, string>;
}

export const translations: Record<Language, Translations> = {
  en: {
    appName: "AnyStream Video Downloader",
    tagline: "Paste any public media link to download in high quality with one click",
    urlPlaceholder: "Paste video link here (e.g. YouTube, Facebook, Vimeo, X...)",
    paste: "Paste",
    clear: "Clear",
    search: "Inspect Link",
    searching: "Analyzing...",
    emptyUrlError: "Please enter a valid video link.",
    invalidUrlError: "Please provide a valid HTTP or HTTPS URL.",
    supportedPlatforms: "Supported platforms:",
    apiOnline: "API Online",
    apiOffline: "Offline",
    apiConnecting: "Connecting",
    changeQualityOrUrl: "Change Quality or URL",
    qualitySectionTitle: "Select Download Quality",
    tabVideo: "Video & Audio",
    tabAudio: "Audio Only",
    selectedQuality: "Selected:",
    bestQuality: "Best Available",
    bestQualityDesc: "Highest resolution (Auto MP4)",
    optimalQuality: "Optimal Quality",
    estSizeAuto: "Est. Size Auto",
    audioOnly: "Audio (MP3 / M4A)",
    mp3Title: "MP3 Audio",
    mp3Desc: "192 kbps • MP3",
    universalCompatible: "Universal Compatible",
    m4aTitle: "M4A Audio",
    m4aDesc: "Direct AAC Stream",
    directAacStream: "Direct AAC Stream",
    resolution: "Quality",
    format: "Format",
    estSize: "Est. Size",
    downloadNow: "Download",
    starting: "Initiating request...",
    queued: "Queued in worker pool...",
    processing: "Downloading & converting media...",
    merging: "Merging audio and video tracks...",
    completed: "Download Ready! 🎉",
    failed: "Download failed.",
    cancelled: "Download cancelled.",
    cancel: "Cancel",
    cancelling: "Cancelling...",
    retry: "Try Again",
    saveFile: "Save Media File",
    speed: "Speed",
    eta: "ETA",
    timeLeft: "Time remaining",
    seconds: "s",
    secureTokenVerified: "Secure token verified • Direct stream",
    linkExpiresIn30Mins: "Link expires in 30 minutes",
    legalNotice: "Legal Notice: Only download media that you own, have explicit permission to download, or that is licensed under public domain or Creative Commons.",
    legalDisclaimer: "AnyStream does not host copyrighted media and respects all digital rights laws.",
    historyTitle: "Download History",
    noHistory: "No recent downloads on this device.",
    clearHistory: "Clear History",
    close: "Close",
    themeLight: "Light Mode",
    themeDark: "Dark Mode",
    terms: "Terms of Service",
    privacy: "Privacy Policy",
    dmca: "DMCA Takedown",
    footerRights: "AnyStream Platform • Powered by Next.js & yt-dlp Core",
    errors: {
      SSRF_DESTINATION_FORBIDDEN: "Access to private or local network IP addresses is restricted for security.",
      MEDIA_DRM_PROTECTED: "This media stream is encrypted by DRM copyright protection and cannot be downloaded.",
      UPSTREAM_EXTRACTOR_DEPRECATED: "The extractor for this video platform is temporarily outdated or broken. Please try again later.",
      UPSTREAM_TIMEOUT: "Connection to the media host timed out. Please try again.",
      RATE_LIMIT_EXCEEDED: "Too many requests. Please wait a minute before searching or downloading again.",
      GLOBAL_CONCURRENCY_CAP_EXCEEDED: "The server is currently at maximum processing capacity. Please retry in a few moments.",
      ACCESS_DENIED: "Access denied. Invalid or missing job authorization token.",
      CAPTCHA_VERIFICATION_FAILED: "Security verification failed. Please complete the CAPTCHA check.",
      STORAGE_CAPACITY_FULL: "Server temporary disk storage is temporarily full. Please retry shortly.",
      MEDIA_PRIVATE_OR_UNAVAILABLE: "This video is private, restricted, or no longer available.",
      MEDIA_LIVESTREAM_UNSUPPORTED: "Live streams cannot be downloaded until the broadcast has fully ended.",
      MEDIA_DURATION_EXCEEDED: "Video duration exceeds the maximum limit (3 hours).",
      UNSUPPORTED_URL_OR_PLATFORM: "This URL or media host is currently unsupported. Please check the URL.",
      MEDIA_LIMIT_EXCEEDED: "This video exceeds platform quotas (maximum allowed file size: 2 GB, max duration: 3 hours).",
      LEGAL_TAKEDOWN_BLOCK: "This URL has been blocked in compliance with a copyright or DMCA takedown notice.",
      REQUEST_VALIDATION_ERROR: "The submitted URL or parameters are invalid.",
      JOB_NOT_FOUND: "Download job not found or has expired (links expire after 30 minutes).",
      DOWNLOAD_TOKEN_INVALID: "Download link has expired or security signature is invalid. Please request a new download.",
      DEFAULT: "Unable to retrieve information for this URL. Please verify the link is publicly accessible.",
    },
  },
  bn: {
    appName: "AnyStream Video Downloader",
    tagline: "যেকোনো পাবলিক ভিডিওর লিংক দিন এবং এক ক্লিকে ডাউনলোড করুন",
    urlPlaceholder: "ভিডিও লিংক পেস্ট করুন (যেমন: YouTube, Facebook, Vimeo...)",
    paste: "পেস্ট",
    clear: "মুছুন",
    search: "সার্চ করুন",
    searching: "তথ্য খোঁজা হচ্ছে...",
    emptyUrlError: "অনুগ্রহ করে একটি বৈধ ভিডিও লিংক দিন।",
    invalidUrlError: "অনুগ্রহ করে একটি সঠিক HTTP বা HTTPS লিংক দিন।",
    supportedPlatforms: "সমর্থিত প্ল্যাটফর্ম:",
    apiOnline: "অনলাইন",
    apiOffline: "অফলাইন",
    apiConnecting: "সংযোগ হচ্ছে",
    changeQualityOrUrl: "কোয়ালিটি বা লিংক পরিবর্তন করুন",
    qualitySectionTitle: "ডাউনলোড কোয়ালিটি নির্বাচন করুন",
    tabVideo: "ভিডিও ও অডিও",
    tabAudio: "শুধুমাত্র অডিও",
    selectedQuality: "নির্বাচিত:",
    bestQuality: "সেরা কোয়ালিটি",
    bestQualityDesc: "সর্বোচ্চ রেজোলিউশন (অটো MP4)",
    optimalQuality: "সর্বোচ্চ মান",
    estSizeAuto: "আনুমানিক সাইজ অটো",
    audioOnly: "অডিও (MP3 / M4A)",
    mp3Title: "MP3 অডিও",
    mp3Desc: "১৯২ কেবিপিএস • MP3",
    universalCompatible: "সর্বজনীন সামঞ্জস্যপূর্ণ",
    m4aTitle: "M4A অডিও",
    m4aDesc: "ডাইরেক্ট AAC স্ট্রিম",
    directAacStream: "ডাইরেক্ট AAC স্ট্রিম",
    resolution: "রেজোলিউশন",
    format: "ফরম্যাট",
    estSize: "সাইজ",
    downloadNow: "ডাউনলোড করুন",
    starting: "রিকোয়েস্ট গ্রহণ করা হচ্ছে...",
    queued: "কিউতে অপেক্ষারত...",
    processing: "ভিডিও ডাউনলোড ও কনভার্ট হচ্ছে...",
    merging: "ভিডিও ও অডিও ট্র্যাক মার্জ হচ্ছে...",
    completed: "ডাউনলোড প্রস্তুত! 🎉",
    failed: "ডাউনলোড ব্যর্থ হয়েছে।",
    cancelled: "ডাউনলোড বাতিল করা হয়েছে।",
    cancel: "বাতিল করুন",
    cancelling: "বাতিল করা হচ্ছে...",
    retry: "আবার চেষ্টা করুন",
    saveFile: "ভিডিও ফাইল সেভ করুন",
    speed: "স্পিড",
    eta: "বাকি সময়",
    timeLeft: "আনুমানিক সময়",
    seconds: "সেকেন্ড",
    secureTokenVerified: "নিরাপদ টোকেন যাচাইকৃত • ডাইরেক্ট স্ট্রিম",
    linkExpiresIn30Mins: "লিংকের মেয়াদ ৩০ মিনিট",
    legalNotice: "আইনি সতর্কতা: শুধুমাত্র সেই সকল কন্টেন্ট ডাউনলোড করুন যার অনুমতি আপনার রয়েছে অথবা যা পাবলিক ডোমেইন / ক্রিয়েটিভ কমন্স লাইসেন্সপ্রাপ্ত।",
    legalDisclaimer: "AnyStream কোনো কপিরাইটযুক্ত ফাইল নিজস্ব সার্ভারে রাখে না এবং মেধা-স্বত্ব আইন মেনে চলে।",
    historyTitle: "ডাউনলোড হিস্ট্রি",
    noHistory: "আপনার ডিভাইসে কোনো সাম্প্রতিক ডাউনলোড নেই।",
    clearHistory: "হিস্ট্রি মুছুন",
    close: "বন্ধ করুন",
    themeLight: "লাইট মোড",
    themeDark: "ডার্ক মোড",
    terms: "ব্যবহারের নিয়মাবলী",
    privacy: "গোপনীয়তা নীতি",
    dmca: "DMCA কপিরাইট নোটিশ",
    footerRights: "AnyStream প্ল্যাটফর্ম • Next.js এবং yt-dlp কোর দ্বারা চালিত",
    errors: {
      SSRF_DESTINATION_FORBIDDEN: "নিরাপত্তাজনিত কারণে লোকাল বা প্রাইভেট আইপি অ্যাড্রেসে অ্যাক্সেস নিষিদ্ধ।",
      MEDIA_DRM_PROTECTED: "এই কন্টেন্টটি DRM এনক্রিপশন দ্বারা সুরক্ষিত এবং ডাউনলোড করা সম্ভব নয়।",
      UPSTREAM_EXTRACTOR_DEPRECATED: "ভিডিও প্ল্যাটফর্মের এক্সট্র্যাক্টরটি সাময়িকভাবে অচল। কিছুক্ষণ পর আবার চেষ্টা করুন।",
      UPSTREAM_TIMEOUT: "মিডিয়া হোস্ট থেকে সাড়া পেতে দেরি হচ্ছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
      RATE_LIMIT_EXCEEDED: "অতিরিক্ত রিকোয়েস্ট পাঠানো হয়েছে। দয়া করে কিছুক্ষণ অপেক্ষা করুন।",
      GLOBAL_CONCURRENCY_CAP_EXCEEDED: "সার্ভারে এই মুহূর্তে অতিরিক্ত কাজের চাপ রয়েছে। অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।",
      ACCESS_DENIED: "অ্যাক্সেস প্রত্যাখ্যান করা হয়েছে। সঠিক টোকেন প্রদান করুন।",
      CAPTCHA_VERIFICATION_FAILED: "সিকিউরিটি যাচাইকরণ ব্যর্থ হয়েছে। ক্যাপচা সম্পন্ন করুন।",
      STORAGE_CAPACITY_FULL: "সার্ভারের স্টোরেজ সাময়িকভাবে পূর্ণ। কিছুক্ষণ পর আবার চেষ্টা করুন।",
      MEDIA_PRIVATE_OR_UNAVAILABLE: "এই ভিডিওটি প্রাইভেট অথবা ডিলিট করা হয়েছে।",
      MEDIA_LIVESTREAM_UNSUPPORTED: "লাইভ সম্প্রচার চলাকালীন ভিডিও ডাউনলোড করা সম্ভব নয়।",
      MEDIA_DURATION_EXCEEDED: "ভিডিওর দৈর্ঘ্য সর্বোচ্চ অনুমোদিত সীমা (৩ ঘণ্টা) অতিক্রম করেছে।",
      UNSUPPORTED_URL_OR_PLATFORM: "এই ওয়েবসাইটের ভিডিও বর্তমানে সাপোর্ট করে না। অনুগ্রহ করে লিংক চেক করুন।",
      MEDIA_LIMIT_EXCEEDED: "ভিডিওর আকার বা সময়সীমা সীমার অতিরিক্ত (সর্বোচ্চ সাইজ: ২ জিবি, সর্বোচ্চ সময়: ৩ ঘণ্টা)।",
      LEGAL_TAKEDOWN_BLOCK: "কপিরাইট নোটিশের কারণে এই লিংকটি ব্লক করা হয়েছে।",
      REQUEST_VALIDATION_ERROR: "প্রদত্ত লিংক বা প্যারামিটার সঠিক নয়।",
      JOB_NOT_FOUND: "ডাউনলোড জব পাওয়া যায়নি অথবা মেয়াদ শেষ হয়ে গেছে (মেয়াদ ৩০ মিনিট)।",
      DOWNLOAD_TOKEN_INVALID: "ডাউনলোড টোকেনের মেয়াদ শেষ হয়ে গেছে। অনুগ্রহ করে নতুন করে ডাউনলোড শুরু করুন।",
      DEFAULT: "ভিডিওর তথ্য আনা সম্ভব হয়নি। লিংকটি পাবলিক ও অ্যাক্সেসযোগ্য কিনা যাচাই করুন।",
    },
  },
};

export function getErrorMessage(errorCode: string | null | undefined, lang: Language): string {
  const dict = translations[lang].errors;
  if (!errorCode) return dict.DEFAULT;
  return dict[errorCode] || dict.DEFAULT;
}
