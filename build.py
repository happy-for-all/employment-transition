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
# 👑 まごころ就労移行支援ナビ: 自動ビルドエンジン (Ver 1.5 全国展開アドオン版)
# 開発者: ちゃろ ＆ AIバディ
# 理念: HFA (Happy for All)
# ==========================================

COORD_OVERRIDES = {
    # 例: "テスト事業所名": {"lat": 34.0, "lon": 135.0},
}

# 👑 【全国展開アドオン】47都道府県：県庁座標 + ファイル名用slug
PREFECTURE_OFFICES = {
    "北海道": {"slug": "hokkaido", "lat": 43.0642, "lon": 141.3469},
    "青森県": {"slug": "aomori", "lat": 40.8244, "lon": 140.7400},
    "岩手県": {"slug": "iwate", "lat": 39.7036, "lon": 141.1527},
    "宮城県": {"slug": "miyagi", "lat": 38.2682, "lon": 140.8721},
    "秋田県": {"slug": "akita", "lat": 39.7186, "lon": 140.1024},
    "山形県": {"slug": "yamagata", "lat": 38.2404, "lon": 140.3633},
    "福島県": {"slug": "fukushima", "lat": 37.7503, "lon": 140.4676},
    "茨城県": {"slug": "ibaraki", "lat": 36.3418, "lon": 140.4468},
    "栃木県": {"slug": "tochigi", "lat": 36.5657, "lon": 139.8836},
    "群馬県": {"slug": "gunma", "lat": 36.3911, "lon": 139.0608},
    "埼玉県": {"slug": "saitama", "lat": 35.8569, "lon": 139.6489},
    "千葉県": {"slug": "chiba", "lat": 35.6047, "lon": 140.1232},
    "東京都": {"slug": "tokyo", "lat": 35.6895, "lon": 139.6917},
    "神奈川県": {"slug": "kanagawa", "lat": 35.4478, "lon": 139.6425},
    "新潟県": {"slug": "niigata", "lat": 37.9026, "lon": 139.0232},
    "富山県": {"slug": "toyama", "lat": 36.6953, "lon": 137.2113},
    "石川県": {"slug": "ishikawa", "lat": 36.5947, "lon": 136.6256},
    "福井県": {"slug": "fukui", "lat": 36.0652, "lon": 136.2216},
    "山梨県": {"slug": "yamanashi", "lat": 35.6642, "lon": 138.5685},
    "長野県": {"slug": "nagano", "lat": 36.6513, "lon": 138.1810},
    "岐阜県": {"slug": "gifu", "lat": 35.3912, "lon": 136.7223},
    "静岡県": {"slug": "shizuoka", "lat": 34.9769, "lon": 138.3831},
    "愛知県": {"slug": "aichi", "lat": 35.1802, "lon": 136.9066},
    "三重県": {"slug": "mie", "lat": 34.7303, "lon": 136.5086},
    "滋賀県": {"slug": "shiga", "lat": 35.0045, "lon": 135.8686},
    "京都府": {"slug": "kyoto", "lat": 35.0210, "lon": 135.7556},
    "大阪府": {"slug": "osaka", "lat": 34.6862, "lon": 135.5201},
    "兵庫県": {"slug": "hyogo", "lat": 34.6913, "lon": 135.1830},
    "奈良県": {"slug": "nara", "lat": 34.6853, "lon": 135.8327},
    "和歌山県": {"slug": "wakayama", "lat": 34.2260, "lon": 135.1675},
    "鳥取県": {"slug": "tottori", "lat": 35.5039, "lon": 134.2378},
    "島根県": {"slug": "shimane", "lat": 35.4723, "lon": 133.0505},
    "岡山県": {"slug": "okayama", "lat": 34.6618, "lon": 133.9344},
    "広島県": {"slug": "hiroshima", "lat": 34.3966, "lon": 132.4596},
    "山口県": {"slug": "yamaguchi", "lat": 34.1859, "lon": 131.4714},
    "徳島県": {"slug": "tokushima", "lat": 34.0658, "lon": 134.5593},
    "香川県": {"slug": "kagawa", "lat": 34.3401, "lon": 134.0434},
    "愛媛県": {"slug": "ehime", "lat": 33.8417, "lon": 132.7661},
    "高知県": {"slug": "kochi", "lat": 33.5597, "lon": 133.5311},
    "福岡県": {"slug": "fukuoka", "lat": 33.6064, "lon": 130.4181},
    "佐賀県": {"slug": "saga", "lat": 33.2494, "lon": 130.2988},
    "長崎県": {"slug": "nagasaki", "lat": 32.7448, "lon": 129.8737},
    "熊本県": {"slug": "kumamoto", "lat": 32.7898, "lon": 130.7417},
    "大分県": {"slug": "oita", "lat": 33.2382, "lon": 131.6126},
    "宮崎県": {"slug": "miyazaki", "lat": 31.9111, "lon": 131.4239},
    "鹿児島県": {"slug": "kagoshima", "lat": 31.5602, "lon": 130.5581},
    "沖縄県": {"slug": "okinawa", "lat": 26.2124, "lon": 127.6809},
}

SERVICE_DEFINITIONS = [
    {
        "zip_file": "sfkopendata_202603_60.zip",
        "service_name": "就労移行支援",
        "output_key": "shuro_transition",
    }
]

# 👑 全国の都府県網羅辞書（市区町村レベル）
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
    "前橋市": {"lat": 36.3895, "lon": 139.0634}
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

def detect_prefecture_key(text):
    """住所文字列の先頭から都道府県名を判定する"""
    for pref in PREFECTURE_OFFICES.keys():
        if text.startswith(pref):
            return pref
    return None

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

    # 👑 【改善適用】ビルド前に dist フォルダをクリアして安全な状態を作る
    dist_root = "dist"
    if os.path.exists(dist_root):
        shutil.rmtree(dist_root)
    
    # 👑 出力先は就労移行支援ナビ用ディレクトリ
    target_dir = os.path.join("dist", "employment-transition")
    os.makedirs(target_dir, exist_ok=True)
    
    summary_logs = []
    manifest = {}   # 👑 【全国展開アドオン】マニフェスト出力用

    for srv_def in SERVICE_DEFINITIONS:
        zip_file_path = srv_def["zip_file"]
        service_name = srv_def["service_name"]
        output_key = srv_def["output_key"]
        
        print(f"\n📡 処理開始: 【{service_name}】 (ファイル: {zip_file_path})")

        # 👑 【安全策適用】sys.exit(1)ではなく、スキップして次へ
        if not os.path.exists(zip_file_path):
            print(f"⚠️ [警告] 『{zip_file_path}』が見つかりません。スキップします。")
            continue

        df = None
        # 👑 【改善適用】zip_file の開始から CSV 読み込みまで全体を with でまとめて安全に囲む
        try:
            with zipfile.ZipFile(zip_file_path) as zip_file:
                csv_files = [f for f in zip_file.namelist() if f.lower().endswith('.csv') and not f.startswith('__MACOSX')]
                
                if not csv_files:
                    raise Exception("CSVファイルが見つかりません。")
                    
                if len(csv_files) > 1:
                    csv_filename = max(csv_files, key=lambda f: zip_file.getinfo(f).file_size)
                else:
                    csv_filename = csv_files[0]
                    
                encodings = ["utf-8-sig", "shift_jis", "cp932", "utf-8"]
                for enc in encodings:
                    try:
                        with zip_file.open(csv_filename) as f:
                            df = pd.read_csv(f, encoding=enc, dtype=str)
                        break
                    except Exception:
                        continue
        except Exception as e:
            # 👑 【安全策適用】スキップして次へ
            print(f"❌ ZIP解凍エラー ({service_name}): {e}")
            continue

        if df is None:
            # 👑 【安全策適用】スキップして次へ
            print(f"❌ CSV読込失敗 ({service_name})。スキップします。")
            continue

        df.columns = df.columns.str.strip().str.replace('\n', '').str.replace('\r', '')

        col_address_city = [col for col in df.columns if "事業所" in col and "住所" in col and "市区町村" in col]
        if not col_address_city:
            # 👑 【安全策適用】スキップして次へ
            print(f"❌ 事業所住所（市区町村）列が見つかりません ({service_name})。スキップします。")
            continue
        target_col = col_address_city[0]

        # 👑 【全国展開アドオン】13都府県 → 全47都道府県へ拡張
        target_prefectures = tuple(PREFECTURE_OFFICES.keys())
        df_filtered = df[df[target_col].astype(str).str.strip().str.startswith(target_prefectures, na=False)].copy()
        
        facilities = []
        
        for _, row in df_filtered.iterrows():
            city = safe_get(row, ["事業所住所（市区町村）", "事業所住所(市区町村)", target_col])
            if not city:
                continue

            name = safe_get(row, ["事業所の名称", "事業所名称"])
            name_kana = safe_get(row, ["事業所の名称_かな", "事業所名称_かな", "フリガナ", "ふりがな"])
            address_detail = safe_get(row, ["事業所住所（番地以降）", "事業所住所(番地以降)"])
            
            # 👑 【改善適用】address_detail の長さ判定を正規化後に行う
            address_detail_normalized = unicodedata.normalize('NFKC', address_detail)
            if not re.search(r'[0-9]', address_detail_normalized) or len(address_detail_normalized) <= 2:
                address_detail = ""
                
            address = city + address_detail

            # 👑 [全国展開につき無効化] target_prefecturesが47都道府県になったため、
            # この二重除外チェックは不要。ロールバック用にコードは残し、判定だけ空にする。
            exclude_keywords = []
            if any(ex_kw in address for ex_kw in exclude_keywords):
                continue

            raw_tel = safe_get(row, ["事業所電話番号", "事業所連絡先", "電話番号"])
            tel_clean = re.sub(r'[^0-9\-]', '', raw_tel.translate(str.maketrans('０１２３４５６７８９', '0123456789')))

            raw_lat = safe_get(row, ["事業所緯度", "緯度"])
            raw_lon = safe_get(row, ["事業所経度", "経度"])
            
            raw_url_text = safe_get(row, ["事業所URL", "事業所ＵＲＬ", "ホームページ", "ホームページアドレス", "法人URL"])
            clean_url = extract_clean_url(raw_url_text)
            
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
                
            # 👑 【全国展開アドオン】47都道府県対応の座標フォールバック
            if lat is None or lon is None:
                is_approximate = True

                detected_pref = detect_prefecture_key(city)
                matched_pref_len = len(detected_pref) if detected_pref else 0

                detected_city = None
                for key in MUNICIPAL_COORDS.keys():
                    if key in city and (city.index(key) == matched_pref_len or city.index(key) == 0):
                        detected_city = key
                        break

                if detected_city:
                    lat = MUNICIPAL_COORDS[detected_city]["lat"]
                    lon = MUNICIPAL_COORDS[detected_city]["lon"]
                elif detected_pref:
                    lat = PREFECTURE_OFFICES[detected_pref]["lat"]
                    lon = PREFECTURE_OFFICES[detected_pref]["lon"]
                else:
                    lat = PREFECTURE_OFFICES["東京都"]["lat"]
                    lon = PREFECTURE_OFFICES["東京都"]["lon"]

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
                "time_weekday": time_weekday,
                "time_saturday": time_saturday,
                "time_sunday": time_sunday,
                "time_holiday": time_holiday,
                "day_off": day_off,
                "notes": notes,
                "capacity": capacity
            })

        # 👑 【全国展開アドオン】都道府県ごとにファイルを分割して書き出す
        facilities_by_pref = {}
        for fac in facilities:
            pref_key = detect_prefecture_key(fac["address"]) or "不明"
            facilities_by_pref.setdefault(pref_key, []).append(fac)

        manifest_for_service = {}
        for pref_key, fac_list in facilities_by_pref.items():
            slug = PREFECTURE_OFFICES.get(pref_key, {}).get("slug", "unknown")
            output_path = os.path.join(target_dir, f"data_{output_key}_{slug}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(fac_list, f, ensure_ascii=False, indent=2)
            manifest_for_service[slug] = len(fac_list)

        manifest[output_key] = manifest_for_service
        summary_logs.append(f" - {service_name}: {len(facilities)}件 → {len(facilities_by_pref)}都道府県に分割完了")

    if os.path.exists("index.html"):
        shutil.copy2("index.html", os.path.join(target_dir, "index.html"))

    # 👑 【全国展開アドオン】フロント側が参照できるよう manifest.json を出力
    manifest_path = os.path.join(target_dir, "data_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    # 👑 【安全策適用】1件もデータが生成されなかった場合のみ、ここで初めてシステムを止める二段構え（変更なし・温存）
    if not summary_logs:
        print("❌ [致命的エラー] 1件も正常にデータが生成されませんでした。ビルドを中断します。")
        sys.exit(1)

    print("\n==========================================")
    for log in summary_logs: print(log)
    print("==========================================")

if __name__ == "__main__":
    try:
        run_build()
    except Exception as e:
        print(f"❌ [未予期エラー] ビルド中に重大なエラーが発生しました: {e}")
        sys.exit(1)
