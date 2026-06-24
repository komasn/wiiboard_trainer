import bluetooth
import time
import sys
import os
import random
from datetime import datetime

# --- 🏃‍♂️ 運動メニューの設定 ---
TRAINING_MENU = [
    {"name": "スクワット", "count": "15回", "desc": "太ももとお尻を意識して、ゆっくり腰を落としましょう！"},
    {"name": "腕立て伏せ", "count": "10回", "desc": "胸を床に近づけるイメージで。キツければ膝をついてもOK！"},
    {"name": "プランク", "count": "30秒", "desc": "体幹を真っ直ぐキープ！お腹に力を入れて耐えて！"},
    {"name": "ふくらはぎ上げ", "count": "20回", "desc": "かかとを上げて、つま先立ちを繰り返します。"},
    {"name": "体幹ストレッチ", "count": "左右各5回", "desc": "ボードの上でゆっくり体を左右にひねりましょう。"}
]

LOG_FILE = "health_log.csv"

# CSVファイルの初期化
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("日時,メニュー,体重(kg)\n")

# --- ⚖️ Wiiバランスボード設定 ---
BD_ADDR = "XX:XX:XX:XX:XX:XX"

def connect_wiiboard():
    print("\nWiiバランスボードに接続を試みています...")
    print("※ボードの裏の赤ボタンをポンと押してください！")
    while True:
        try:
            ctl_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
            inter_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
            ctl_sock.connect((BD_ADDR, 0x11))
            inter_sock.connect((BD_ADDR, 0x13))
            print("🎉 ボードと接続しました！")
            inter_sock.send(bytes([0xa2, 0x11, 0x10]))
            time.sleep(0.1)
            inter_sock.send(bytes([0xa2, 0x12, 0x00, 0x34]))
            time.sleep(0.1)
            return inter_sock
        except bluetooth.BluetoothError:
            time.sleep(1.0)

def main():
    os.system('clear')
    print("=========================================")
    print("       🏋️‍♂️ ターミナル・宅トレ相棒アプリ 🏋️‍♂️       ")
    print("=========================================\n")
    
    today_menu = random.choice(TRAINING_MENU)
    print(f"🔥 今日の筋トレ指令：【 {today_menu['name']} 】 を {today_menu['count']}！")
    print(f"💡 コツ：{today_menu['desc']}\n")
    print("-----------------------------------------")
    input("運動が終わったら、Wiiボードの前に立って[Enter]を押してね！")
    
    inter_sock = connect_wiiboard()
    print("\n⚖️ センサー初期化中... ボードに乗らずにお待ちください...")
    
    baseline_sensors = { 'rf': None, 'rr': None, 'lf': None, 'lr': None }
    samples = { 'rf': [], 'rr': [], 'lf': [], 'lr': [] }
    skip_counter = 0
    
    stable_count = 0
    last_weight = 0
    
    try:
        while True:
            data = inter_sock.recv(32)
            if len(data) >= 11 and data[1] == 0x34:
                
                # 💡 【修正】まず最初に1000回完全にスキップしてパケットを安定させる
                if skip_counter < 1000:
                    skip_counter += 1
                    if skip_counter % 200 == 0:
                        sys.stdout.write(f"\r準備中... ({skip_counter}/1000)")
                        sys.stdout.flush()
                    continue
                
                val_rf = (data[4] << 8) | data[5]
                val_rr = (data[6] << 8) | data[7]
                val_lf = (data[8] << 8) | data[9]
                val_lr = (data[10] << 8) | data[11] if len(data) >= 12 else 0
                
                # 💡 【修正】安定したデータが来てから、20回分で0点調整を計算する
                if baseline_sensors['rf'] == None:
                    samples['rf'].append(val_rf)
                    samples['rr'].append(val_rr)
                    samples['lf'].append(val_lf)
                    samples['lr'].append(val_lr)
                    if len(samples['rf']) >= 20:
                        baseline_sensors['rf'] = sum(samples['rf']) / 20
                        baseline_sensors['rr'] = sum(samples['rr']) / 20
                        baseline_sensors['lf'] = sum(samples['lf']) / 20
                        baseline_sensors['lr'] = sum(samples['lr']) / 20
                        print("\n\n⚖️ 準備完了！ボードに乗って直立してください。\n")
                    continue
                
                rf = max(0, val_rf - baseline_sensors['rf'])
                rr = max(0, val_rr - baseline_sensors['rr'])
                lf = max(0, val_lf - baseline_sensors['lf'])
                lr = max(0, val_lr - baseline_sensors['lr'])
                
                total = rf + rr + lf + lr
                weight_kg = total / 102.9
                
                if weight_kg > 20.0:
                    sys.stdout.write(f"\r測定中... 現在の体重: {weight_kg:.1f} kg")
                    sys.stdout.flush()
                    
                    if abs(weight_kg - last_weight) < 0.2:
                        stable_count += 1
                    else:
                        stable_count = 0
                    
                    last_weight = weight_kg
                    
                    if stable_count >= 30:
                        print(f"\n\n🎯 測定完了！ 今日の体重: {weight_kg:.1f} kg")
                        
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with open(LOG_FILE, "a", encoding="utf-8") as f:
                            f.write(f"{now_str},{today_menu['name']},{weight_kg:.1f}\n")
                        
                        print(f"💾 {LOG_FILE} にアクティビティを記録しました！")
                        print("\n🌟 今日も素晴らしい努力です！明日も一緒に頑張りましょう！ 🌟")
                        break
                else:
                    sys.stdout.write("\rボードに乗ってください...                             ")
                    sys.stdout.flush()
                    stable_count = 0
                
                time.sleep(0.005)
                
    except KeyboardInterrupt:
        print("\nアプリを終了します。")
    finally:
        inter_sock.close()

if __name__ == "__main__":
    main()
