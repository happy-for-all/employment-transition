import os
import json
import sys
import zipfile
import io
import re
import pandas as pd
import unicodedata
import math
import shutil

# ==========================================
# 👑 まごころ就労移行支援ナビ: 自動ビルドエンジン (Ver 1.1)
# 開発者: ちゃろ ＆ AIバディ
# 理念: HFA (Happy for All)
# ==========================================

# 👑 行政データの座標ミスを手動で補正するオーバーライド辞書（必要に応じて追加）
COORD_OVERRIDES = {
    # 例: "テスト事業所名": {"lat": 34.0, "lon": 135.0},
}

# 👑 今回ダウンロードした「就労移行支援」のZIPを設定
SERVICE_DEFINITIONS = [
    {
        "zip_file": "sfkopendata_202603_60.zip",
        "service_name": "就労移行支援",
        "output_key": "shuro_transition",
    }
]

# 👑 HFA版と完全に同期した13都府県網羅辞書
MUNICIPAL_COORDS = {
    # 🌿 関西（大阪府）
    "大阪市": {"lat": 34.6937, "lon": 135.5022},
    "堺市": {"lat": 34.5714, "lon": 135.4807},
    "東大阪市": {"lat": 34.6793, "lon": 135.5999},
    "豊中市": {"lat": 34.7816, "lon": 135.4698},
    "枚方市": {"lat": 34.8162, "lon": 135.6500},
    "吹田市": {"lat": 34.7649, "lon": 135.5140},
    "高槻市": {"lat": 34.8486, "lon": 135.6175},
    "八尾市": {"lat": 34.6293, "lon": 135.6022},
    "寝屋川市": {"lat": 34.7644, "lon": 135.6262},
    "岸和田市": {"lat": 34.4619, "lon": 135.3750},
    "和泉市": {"lat": 34.4883, "lon": 135.4241},
    "守口市": {"lat": 34.7344, "lon": 135.5620},
    "門真市": {"lat": 34.7410, "lon": 135.5911},
    "箕面市": {"lat": 34.8271, "lon": 135.4704},
    "大東市": {"lat": 34.7121, "lon": 135.6224},
    "松原市": {"lat": 34.5772, "lon": 135.5562},
    "富田林市": {"lat": 34.5009, "lon": 135.6019},
    "羽曳野市": {"lat": 34.5583, "lon": 135.6075},
    "河内長野市": {"lat": 34.4536, "lon": 135.5658},
    "池田市": {"lat": 34.8258, "lon": 135.4294},
    "泉佐野市": {"lat": 34.4103, "lon": 135.3262},
    "貝塚市": {"lat": 34.4372, "lon": 135.3589},
    "摂津市": {"lat": 34.7516, "lon": 135.5619},
    "交野市": {"lat": 34.7850, "lon": 135.6811},
    "四條畷市": {"lat": 34.7291, "lon": 135.6413},
    "柏原市": {"lat": 34.5802, "lon": 135.6258},
    "藤井寺市": {"lat": 34.5750, "lon": 135.5969},
    "泉大津市": {"lat": 34.5022, "lon": 135.4058},
    "高石市": {"lat": 34.5219, "lon": 135.4380},
    "大阪狭山市": {"lat": 34.5036, "lon": 135.5519},
    "阪南市": {"lat": 34.3592, "lon": 135.2442},
    "泉南市": {"lat": 34.3725, "lon": 135.2758},
    
    # 🌿 関西（大阪以外）
    "京都市": {"lat": 35.0116, "lon": 135.7680},
    "神戸市": {"lat": 34.6901, "lon": 135.1955},
    "姫路市": {"lat": 34.8151, "lon": 134.6853},
    "西宮市": {"lat": 34.7377, "lon": 135.3418},
    "尼崎市": {"lat": 34.7335, "lon": 135.4063},
    "奈良市": {"lat": 34.6851, "lon": 135.8048},
    "和歌山市": {"lat": 34.2305, "lon": 135.1706},
    "大津市": {"lat": 35.0145, "lon": 135.8522},

    # 🌿 関東（東京都）
    "千代田区": {"lat": 35.6940, "lon": 139.7536},
    "中央区": {"lat": 35.6706, "lon": 139.7718},
    "港区": {"lat": 35.6580, "lon": 139.7515},
    "新宿区": {"lat": 35.6938, "lon": 139.7035},
    "文京区": {"lat": 35.7080, "lon": 139.7521},
    "台東区": {"lat": 35.7126, "lon": 139.7799},
    "墨田区": {"lat": 35.7107, "lon": 139.8014},
    "江東区": {"lat": 35.6728, "lon": 139.8174},
    "品川区": {"lat": 35.6092, "lon": 139.7301},
    "目黒区": {"lat": 35.6414, "lon": 139.6981},
    "大田区": {"lat": 35.5612, "lon": 139.7160},
    "世田谷区": {"lat": 35.6465, "lon": 139.6532},
    "渋谷区": {"lat": 35.6617, "lon": 139.7040},
    "中野区": {"lat": 35.7073, "lon": 139.6638},
    "杉並区": {"lat": 35.6995, "lon": 139.6364},
    "豊島区": {"lat": 35.7261, "lon": 139.7166},
    "北区": {"lat": 35.7528, "lon": 139.7334},
    "荒川区": {"lat": 35.7360, "lon": 139.7833},
    "板橋区": {"lat": 35.7511, "lon": 139.7092},
    "練馬区": {"lat": 35.7356, "lon": 139.6516},
    "足立区": {"lat": 35.7756, "lon": 139.8044},
    "葛飾区": {"lat": 35.7435, "lon": 139.8471},
    "江戸川区": {"lat": 35.7066, "lon": 139.8684},
    "八王子市": {"lat": 35.6663, "lon": 139.3158},
    "町田市": {"lat": 35.5466, "lon": 139.4386},
    "府中市": {"lat": 35.6689, "lon": 139.4776},
    "調布市": {"lat": 35.6506, "lon": 139.5406},
    "西東京市": {"lat": 35.7252, "lon": 139.5398},
    "小平市": {"lat": 35.7285, "lon": 139.4774},
    "三鷹市": {"lat": 35.6835, "lon": 139.5595},
    "日野市": {"lat": 35.6713, "lon": 139.3949},
    "立川市": {"lat": 35.7140, "lon": 139.4078},
    
    # 🌿 関東（東京以外）
    "横浜市": {"lat": 35.4478, "lon": 139.6425},
    "川崎市": {"lat": 35.5308, "lon": 139.7029},
    "さいたま市": {"lat": 35.8617, "lon": 139.6455},
    "千葉市": {"lat": 35.6073, "lon": 140.1063},
    "水戸市": {"lat": 36.3659, "lon": 140.4712},
    "宇都宮市": {"lat": 36.5551, "lon": 139.8826},
    "前橋市": {"lat": 36.3895, "lon": 139.0634},

    # 👑 最終手段のフェイルセーフ（各府県庁）
    "フェイルセーフ東京都庁": {"lat": 35.6895, "lon": 139.6917},
    "フェイルセーフ神奈川県庁": {"lat": 35.4478, "lon": 139.6425},
    "フェイルセーフ埼玉県庁": {"lat": 35.8569, "lon": 139.6489},
    "フェイルセーフ千葉県庁": {"lat": 35.6047, "lon": 140.1232},
    "フェイルセーフ茨城県庁": {"lat": 36.3418, "lon": 140.4468},
    "フェイルセーフ栃木県庁": {"lat": 36.5657, "lon": 139.8836},
    "フェイルセーフ群馬県庁": {"lat": 36.3911, "lon": 139.0608},
    "フェイルセーフ大阪府庁": {"lat": 34.6862, "lon": 135.5201},
    "フェイルセーフ京都府庁": {"lat": 35.0210, "lon": 135.7556},
    "フェイルセーフ兵庫県庁": {"lat": 34.6913, "lon": 135.1830},
    "フェイルセーフ奈良県庁": {"lat": 34.6853, "lon": 135.8327},
    "フェイルセーフ和歌山県庁": {"lat": 34.2260, "lon": 135.1675},
    "フェイルセーフ滋賀県庁": {"lat": 35.0045, "lon": 135.8686}
}

def safe_get(row, possible_keys):
    for key in possible_keys:
        if key in row:
            if pd.isna(row[key]):
                continue
            value = str(row[key]).strip()
            if value.lower() == "nan" or value == "":
                continue
            return value
    return ""

def extract_clean_url(raw_text):
    if not raw_text or pd.isna(raw_text):
        return ""
    text = unicodedata.normalize('NFKC', str(raw_text)).replace('\n', '').replace('\r', '').strip()
    url_pattern = re.compile(r'(?:https?://|www\.)[a-zA-Z0-9\.\-\_]+[\w/\:\%\#\$\&\?\(\)\~\.\=\+\-]*')
    match = url_pattern.search(text)
    if match:
        extracted = match.group(0)
        if extracted.startswith("www."):
            extracted = "https://" + extracted
        extracted = extracted.rstrip('\'"）)]}>')
        if len(extracted) <= 8 and extracted.endswith("://"):
            return ""
        return extracted
    return ""

# 👑 住所整形関数（最強版）
def extract_map_address(address):
    if not address:
        return address
    s = unicodedata.normalize('NFKC', address)
    s = re.sub(r'[\u2010-\u2015\u2212\uFF0D]', '-', s)

    chome = r'(?:[0-9]+条[西東南北]?)?[0-9]+丁目'
    ban   = r'[0-9]+番地?'
    gou   = r'[0-9]+号'
    blocknum = r'[0-9]+(?:-[0-9]+)?'

    pattern = re.compile(
        rf'(?:{chome})?(?:{ban})?{gou}'
        rf'|(?:{chome})?{ban}'
        rf'|{chome}{blocknum}'
        rf'|{chome}'
        rf'|[0-9]+-[0-9]+-[0-9]+'
        rf'|[0-9]+-[0-9]+'
    )
    m = pattern.search(s)
    return s[:m.end()].strip() if m else s

def run_build():
    print("==========================================")
    print(f"🌸 まごころ就労移行支援ナビ 自動ビルド開始")
    print("==========================================")

    target_dir = os.path.join("dist", "employment-transition")
    os.makedirs(target_dir, exist_ok=True)
    
    summary_logs = []

    for srv_def in SERVICE_DEFINITIONS:
        zip_file_path = srv_def["zip_file"]
        service_name = srv_def["service_name"]
        output_key = srv_def["output_key"]
        
        print(f"\n📡 処理開始: 【{service_name}】 (ファイル: {zip_file_path})")

        if not os.path.exists(zip_file_path):
            print(f"❌ [エラー] 『{zip_file_path}』が見つかりません。")
            sys.exit(1)

        try:
            zip_file = zipfile.ZipFile(zip_file_path)
            csv_files = [f for f in zip_file.namelist() if f.lower().endswith('.csv') and not f.startswith('__MACOSX')]
            
            if not csv_files:
                raise Exception("CSVファイルが見つかりません。")
                
            if len(csv_files) > 1:
                csv_filename = max(csv_files, key=lambda f: zip_file.getinfo(f).file_size)
            else:
                csv_filename = csv_files[0]
                
        except Exception as e:
            print(f"❌ ZIP解凍エラー ({service_name}): {e}")
            sys.exit(1)

        df = None
        encodings = ["utf-8-sig", "shift_jis", "cp932", "utf-8"]
        for enc in encodings:
            try:
                with zip_file.open(csv_filename) as f:
                    df = pd.read_csv(f, encoding=enc, dtype=str)
                break
            except Exception:
                continue

        if df is None:
            print(f"❌ CSV読込失敗 ({service_name})。ビルドを中止します。")
            sys.exit(1)

        df.columns = df.columns.str.strip().str.replace('\n', '').str.replace('\r', '')

        # 👑 法人住所を絶対に拾わない市区町村列検出
        col_address_city = [col for col in df.columns if "事業所" in col and "住所" in col and "市区町村" in col]
        if not col_address_city:
            print(f"❌ 事業所住所（市区町村）列が見つかりません。ビルドを中止します。")
            sys.exit(1)
        target_col = col_address_city[0]

        # 👑 13都府県ターゲットフィルタリング
        target_prefectures = (
            "東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県",
            "大阪府", "京都府", "兵庫県", "奈良県", "和歌山県", "滋賀県"
        )
        df_filtered = df[df[target_col].astype(str).str.strip().str.startswith(target_prefectures, na=False)].copy()
        
        facilities = []
        
        for _, row in df_filtered.iterrows():
            name = safe_get(row, ["事業所の名称", "事業所名称"])
            name_kana = safe_get(row, ["事業所の名称_かな", "事業所名称_かな", "フリガナ", "ふりがな"])
            
            city = safe_get(row, ["事業所住所（市区町村）", "事業所住所(市区町村)", target_col])
            address_detail = safe_get(row, ["事業所住所（番地以降）", "事業所住所(番地以降)"])
            
            if not re.search(r'[0-9０-９]', address_detail) or len(address_detail) <= 2:
                address_detail = ""
            address = city + address_detail
            
            # 対象外エリアのブロック
            exclude_keywords = [
                "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
                "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県",
                "三重県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
                "徳島県", "香川県", "愛媛県", "高知県",
                "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
            ]
            if any(ex_kw in address for ex_kw in exclude_keywords):
                continue

            raw_tel = safe_get(row, ["事業所電話番号", "事業所連絡先", "電話番号"])
            tel_clean = re.sub(r'[^0-9\-]', '', raw_tel.translate(str.maketrans('０１２３４５６７８９', '0123456789')))

            raw_lat = safe_get(row, ["事業所緯度", "緯度"])
            raw_lon = safe_get(row, ["事業所経度", "経度"])
            
            raw_url_text = safe_get(row, ["事業所URL", "事業所ＵＲＬ", "ホームページ", "ホームページアドレス", "法人URL"])
            clean_url = extract_clean_url(raw_url_text)
            
            # 👑 【追加アドオン項目】詳細情報の安全な取得
            time_weekday = safe_get(row, ["利用可能な時間帯（平日）"])
            time_saturday = safe_get(row, ["利用可能な時間帯（土曜）"])
            time_sunday = safe_get(row, ["利用可能な時間帯（日曜）"])
            time_holiday = safe_get(row, ["利用可能な時間帯（祝日）"])
            day_off = safe_get(row, ["定休日"])
            notes = safe_get(row, ["利用可能曜日特記事項（留意事項）"])
            capacity = safe_get(row, ["定員"])

            lat, lon = None, None
            is_approximate = False
            
            try:
                if raw_lat: lat = float(raw_lat)
                if raw_lon: lon = float(raw_lon)
            except Exception:
                pass
                
            if lat is not None and math.isnan(lat): lat = None
            if lon is not None and math.isnan(lon): lon = None
                
            if lat is None or lon is None:
                is_approximate = True
                
                # 👑 4文字県（神奈川県、和歌山県など）を正確に判定するロジック
                matched_pref_len = 0
                for pref in target_prefectures:
                    if city.startswith(pref):
                        matched_pref_len = len(pref)
                        break
                        
                detected_city = None
                for key in MUNICIPAL_COORDS.keys():
                    if key in city and (city.index(key) == matched_pref_len or city.index(key) == 0):
                        detected_city = key
                        break
                        
                if detected_city:
                    lat = MUNICIPAL_COORDS[detected_city]["lat"]
                    lon = MUNICIPAL_COORDS[detected_city]["lon"]
                else:       
                    if city.startswith("東京都"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ東京都庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ東京都庁"]["lon"]
                    elif city.startswith("神奈川県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ神奈川県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ神奈川県庁"]["lon"]
                    elif city.startswith("埼玉県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ埼玉県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ埼玉県庁"]["lon"]
                    elif city.startswith("千葉県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ千葉県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ千葉県庁"]["lon"]
                    elif city.startswith("茨城県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ茨城県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ茨城県庁"]["lon"]
                    elif city.startswith("栃木県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ栃木県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ栃木県庁"]["lon"]
                    elif city.startswith("群馬県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ群馬県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ群馬県庁"]["lon"]
                    elif city.startswith("京都府"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ京都府庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ京都府庁"]["lon"]
                    elif city.startswith("兵庫県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ兵庫県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ兵庫県庁"]["lon"]
                    elif city.startswith("奈良県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ奈良県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ奈良県庁"]["lon"]
                    elif city.startswith("和歌山県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ和歌山県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ和歌山県庁"]["lon"]
                    elif city.startswith("滋賀県"): lat, lon = MUNICIPAL_COORDS["フェイルセーフ滋賀県庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ滋賀県庁"]["lon"]
                    else: lat, lon = MUNICIPAL_COORDS["フェイルセーフ大阪府庁"]["lat"], MUNICIPAL_COORDS["フェイルセーフ大阪府庁"]["lon"]

            if name in COORD_OVERRIDES:
                lat = COORD_OVERRIDES[name]["lat"]
                lon = COORD_OVERRIDES[name]["lon"]
                is_approximate = False
            
            facilities.append({
                "name": name,
                "name_kana": name_kana,
                "service_type": service_name,   
                "address": address,
                "map_address": extract_map_address(address),
                "tel": raw_tel,
                "tel_clean": tel_clean,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "url": clean_url,
                "is_approximate": is_approximate,
                # 👑 【追加アドオン項目】JSONへの格納
                "time_weekday": time_weekday,
                "time_saturday": time_saturday,
                "time_sunday": time_sunday,
                "time_holiday": time_holiday,
                "day_off": day_off,
                "notes": notes,
                "capacity": capacity
            })

        output_path = os.path.join(target_dir, f"data_{output_key}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(facilities, f, ensure_ascii=False, indent=2)
            
        summary_logs.append(f" - {service_name}: {len(facilities)}件 生成完了")

    shutil.copy2("index.html", os.path.join(target_dir, "index.html"))
    
    print("\n==========================================")
    for log in summary_logs: print(log)
    print("==========================================")

if __name__ == "__main__":
    try:
        run_build()
    except Exception as e:
        print(f"❌ [未予期エラー] ビルド中に重大なエラーが発生しました: {e}")
        sys.exit(1)
