/**
 * 旅遊行程卡片的 emoji 選擇器：關鍵字搜尋 + 依觸發按鈕定位的浮層。
 *
 * 從 pages/app/trips.vue 抽出來。emoji 對照表（含中文關鍵字）也一併移進來，
 * 它佔了原本頁面開頭三十行的常數區。
 *
 * `onPick` 由呼叫端提供：選到 emoji 之後要做什麼（trips 是寫進表單並送出 PATCH）
 * 屬於呼叫端的職責，選擇器本身不該知道。
 */

/** emoji 與搜尋關鍵字（`k` 是給 includes 比對用的中文關鍵字串）。 */
const EMOJI_MAP: Array<{ e: string; k: string }> = [
  // 景點
  { e: '🏯', k: '城堡古蹟景點' }, { e: '🗼', k: '塔景點東京' }, { e: '⛩️', k: '鳥居神社景點' },
  { e: '🎡', k: '摩天輪遊樂場景點' }, { e: '🎢', k: '雲霄飛車遊樂場' }, { e: '🏛️', k: '博物館景點' },
  { e: '🗽', k: '自由女神像景點紐約' }, { e: '🏟️', k: '體育場競技場' }, { e: '🌊', k: '海浪海洋' },
  { e: '🏔️', k: '山景點高山' }, { e: '🗻', k: '富士山景點' }, { e: '🌋', k: '火山景點' },
  { e: '🏝️', k: '小島景點' }, { e: '🏖️', k: '海灘沙灘景點' }, { e: '🌅', k: '日出日落景點' },
  { e: '🌉', k: '夜晚橋景點' }, { e: '🌄', k: '山日出景點' }, { e: '🌃', k: '夜景城市景點' },
  // 美食
  { e: '🍜', k: '拉麵麵食美食' }, { e: '🍣', k: '壽司生魚片日本美食' }, { e: '🍱', k: '便當美食' },
  { e: '🍛', k: '咖哩美食' }, { e: '🍲', k: '火鍋鍋物美食' }, { e: '🍤', k: '炸蝦天婦羅美食' },
  { e: '🥘', k: '燉菜美食鍋物' }, { e: '🍷', k: '紅酒葡萄酒' }, { e: '🍻', k: '啤酒' },
  { e: '☕', k: '咖啡飲料' }, { e: '🍰', k: '蛋糕甜點' }, { e: '🍕', k: '披薩美食' },
  { e: '🍔', k: '漢堡美食' }, { e: '🥗', k: '沙拉' }, { e: '🧇', k: '鬆餅早餐' }, { e: '🍦', k: '冰淇淋甜點' },
  // 交通
  { e: '✈️', k: '飛機航班交通' }, { e: '🚂', k: '火車交通' }, { e: '🚌', k: '公車交通' },
  { e: '🚕', k: '計程車Uber交通' }, { e: '🚗', k: '租車自駕交通' }, { e: '🛵', k: '機車摩托車交通' },
  { e: '🚲', k: '腳踏車單車交通' }, { e: '🚢', k: '郵輪船交通' }, { e: '🚁', k: '直升機交通' },
  { e: '⛵', k: '帆船交通' }, { e: '🚐', k: '小巴交通' }, { e: '🛺', k: '嘟嘟車交通' },
  { e: '🏎️', k: '賽車' }, { e: '🛳️', k: '大船郵輪交通' },
  // 住宿
  { e: '🏨', k: '飯店旅館住宿' }, { e: '🏠', k: '民宿家住宿' }, { e: '🛖', k: '小屋住宿' },
  { e: '⛺', k: '露營帳篷住宿' }, { e: '🏕️', k: '露營住宿' }, { e: '🛏️', k: '床睡覺住宿' },
  // 其他
  { e: '📷', k: '相機拍照' }, { e: '🎫', k: '票券門票' }, { e: '🎟️', k: '票券' },
  { e: '🛍️', k: '購物' }, { e: '🎒', k: '背包' }, { e: '🧳', k: '行李箱行李' },
  { e: '🗺️', k: '地圖' }, { e: '🧭', k: '指南針' }, { e: '📍', k: '地標位置' },
  { e: '📌', k: '圖釘標記' }, { e: '❤️', k: '愛心最愛' }, { e: '⭐', k: '星星推薦' },
  { e: '🌸', k: '櫻花花' }, { e: '🎉', k: '慶祝' }, { e: '💡', k: '提示注意' }, { e: '🔑', k: '鑰匙' },
]

const PICKER_W = 320
const PICKER_H = 310

export function useEmojiPicker(onPick: (emoji: string) => void) {
  const emojiTriggerEl = ref<HTMLButtonElement | null>(null)
  const showEmojiPicker = ref(false)
  const emojiSearch = ref('')
  const emojiPickerStyle = ref<Record<string, string>>({})

  const filteredEmojis = computed(() => {
    const q = emojiSearch.value.trim()
    if (!q) return EMOJI_MAP.map(e => e.e)
    return EMOJI_MAP.filter(({ k }) => k.includes(q)).map(e => e.e)
  })

  function toggleEmojiPicker() {
    if (showEmojiPicker.value) {
      showEmojiPicker.value = false
      return
    }
    if (!emojiTriggerEl.value) return
    const rect = emojiTriggerEl.value.getBoundingClientRect()
    let top = rect.bottom + 6
    let left = rect.left

    // Clamp horizontally
    if (left + PICKER_W > window.innerWidth - 8) {
      left = window.innerWidth - PICKER_W - 8
    }
    if (left < 8) left = 8

    // Flip upward if not enough space below
    if (top + PICKER_H > window.innerHeight - 8) {
      top = rect.top - PICKER_H - 6
    }

    emojiPickerStyle.value = { top: `${top}px`, left: `${left}px` }
    emojiSearch.value = ''
    showEmojiPicker.value = true
  }

  function pickEmoji(e: string) {
    onPick(e)
    showEmojiPicker.value = false
  }

  function closeEmojiPicker() {
    showEmojiPicker.value = false
  }

  return {
    emojiTriggerEl,
    showEmojiPicker,
    emojiSearch,
    emojiPickerStyle,
    filteredEmojis,
    toggleEmojiPicker,
    pickEmoji,
    closeEmojiPicker,
  }
}
