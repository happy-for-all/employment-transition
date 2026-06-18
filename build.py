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
# 👑 まごころ就労移行支援ナビ: 自動ビルドエンジン (Ver 1.3 堅牢化アドオン版)
# 開発者: ちゃろ ＆ AIバディ
# 理念: HFA (Happy for All)
# ==========================================

COORD_OVERRIDES = {
    # 例: "テスト事業所名": {"lat": 34.0, "lon": 135.0},
}

SERVICE_DEFINITIONS = [
    {
        "zip_file": "sfkopendata_202603_60.zip",
        "service_name": "就労移行支援",
        "output_key": "shuro_transition",
    }
]

FAILSAFE_COORDS = {
    "北海道": {"lat": 43.0642, "lon": 141.3469}, "青森県": {"lat": 40.8244, "lon": 140.7400},
    "岩手県": {"lat": 39.7036, "lon": 141.1525}, "宮城県": {"lat": 38.2682, "lon": 140.8694},
    "秋田県": {"lat": 39.7186, "lon": 140.1025}, "山形県": {"lat": 38.2404, "lon": 140.3633},
    "福島県": {"lat": 37.7608, "lon": 140.4748}, "茨城県": {"lat": 36.3418, "lon": 140.4468},
    "栃木県": {"lat": 36.5657, "lon": 139.8836}, "群馬県": {"lat": 36.3911, "lon": 139.0608},
    "埼玉県": {"lat": 35.8569, "lon": 139.6489}, "千葉県": {"lat": 35.6047, "lon": 140.1232},
    "東京都": {"lat": 35.6895, "lon": 139.6917}, "神奈川県": {"lat": 35.4478, "lon": 139.6425},
    "新潟県": {"lat": 37.9022, "lon": 139.0236}, "富山県": {"lat": 36.6953, "lon": 137.2113},
    "石川県": {"lat": 36.5944, "lon": 136.6256}, "福井県": {"lat": 36.0641, "lon": 136.2219},
    "山梨県": {"lat": 35.6639, "lon": 138.5683}, "長野県": {"lat": 36.6513, "lon": 138.1812},
    "岐阜県": {"lat": 35.3912, "lon": 136.7223}, "静岡県": {"lat": 34.9769, "lon": 138.3831},
    "愛知県": {"lat": 35.1802, "lon": 136.9066}, "三重県": {"lat": 34.7303, "lon": 136.5086},
    "滋賀県": {"lat": 35.0045, "lon": 135.8686}, "京都府": {"lat": 35.0210, "lon": 135.7556},
    "大阪府": {"lat": 34.6862, "lon": 135.5201}, "兵庫県": {"lat": 34.6913, "lon": 135.1830},
    "奈良県": {"lat": 34.6853, "lon": 135.8327}, "和歌山県": {"lat": 34.2260, "lon": 135.1675},
    "鳥取県": {"lat": 35.5011, "lon": 134.2351}, "島根県": {"lat": 35.4723, "lon": 133.0505},
    "岡山県": {"lat": 34.6618, "lon": 133.9344}, "広島県": {"lat": 34.3963, "lon": 132.4594},
    "山口県": {"lat": 34.1859, "lon": 131.4714}, "徳島県": {"lat": 34.0657, "lon": 134.5594},
    "香川県": {"lat": 34.3401, "lon": 134.0434}, "愛媛県": {"lat": 33.8416, "lon": 132.7661},
    "高知県": {"lat": 33.5597, "lon": 133.5311}, "福岡県": {"lat": 33.5902, "lon": 130.4017},
    "佐賀県": {"lat": 33.2494, "lon": 130.2998}, "長崎県": {"lat": 32.7503, "lon": 129.8777},
    "熊本県": {"lat": 32.7898, "lon": 130.7417}, "大分県": {"lat": 33.2382, "lon": 131.6126},
    "宮崎県": {"lat": 31.9111, "lon": 131.4239}, "鹿児島県": {"lat": 31.5602, "lon": 130.5581},
    "沖縄県": {"lat": 26.2124, "lon": 127.6809}
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

    # 👑 【改善提案適用】ビルド前に dist フォルダをクリアして安全な状態を作る
    dist_root = "dist"
    if os.path.exists(dist_root):
        shutil.rmtree(dist_root)
    
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

        df = None
        # 👑 【要修正適用】zip_file の開始から CSV 読み込みまで全体を with でまとめて安全に囲む
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
            print(f"❌ ZIP解凍エラー ({service_name}): {e}")
            sys.exit(1)

        if df is None:
            print(f"❌ CSV読込失敗 ({service_name})。ビルドを中止します。")
            sys.exit(1)

        df.columns = df.columns.str.strip().str.replace('\n', '').str.replace('\r', '')

        col_address_city = [col for col in df.columns if "事業所" in col and "住所" in col and "市区町村" in col]
        if not col_address_city:
            print(f"❌ 事業所住所（市区町村）列が見つかりません。ビルドを中止します。")
            sys.exit(1)
        target_col = col_address_city[0]

        df_filtered = df.copy()
        facilities = []
        
        for _, row in df_filtered.iterrows():
            city = safe_get(row, ["事業所住所（市区町村）", "事業所住所(市区町村)", target_col])
            if not city:
                continue

            name = safe_get(row, ["事業所の名称", "事業所名称"])
            name_kana = safe_get(row, ["事業所の名称_かな", "事業所名称_かな", "フリガナ", "ふりがな"])
            address_detail = safe_get(row, ["事業所住所（番地以降）", "事業所住所(番地以降)"])
            
            # 👑 【改善提案適用】address_detail の長さ判定を正規化後に行う
            address_detail_normalized = unicodedata.normalize('NFKC', address_detail)
            if not re.search(r'[0-9]', address_detail_normalized) or len(address_detail_normalized) <= 2:
                address_detail = ""
                
            address = city + address_detail

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
                
            if lat is None or lon is None:
                is_approximate = True
                
                matched_pref = None
                for pref in FAILSAFE_COORDS.keys():
                    if city.startswith(pref):
                        matched_pref = pref
                        break
                        
                if matched_pref:
                    lat = FAILSAFE_COORDS[matched_pref]["lat"]
                    lon = FAILSAFE_COORDS[matched_pref]["lon"]
                else:
                    # 👑 【要修正適用】もし県名が判定できない場合は最後の砦として東京にする
                    lat = FAILSAFE_COORDS["東京都"]["lat"]
                    lon = FAILSAFE_COORDS["東京都"]["lon"]

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

        output_path = os.path.join(target_dir, f"data_{output_key}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(facilities, f, ensure_ascii=False, indent=2)
            
        summary_logs.append(f" - {service_name}: {len(facilities)}件 生成完了 (全国版)")

    if os.path.exists("index.html"):
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
