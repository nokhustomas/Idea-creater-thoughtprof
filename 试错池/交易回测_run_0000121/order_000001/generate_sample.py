import os, datetime, random, csv

def generate():
    os.makedirs('sample_data', exist_ok=True)
    random.seed(42)
    start = datetime.date(2024, 1, 1)
    def next_business_day(d):
        d += datetime.timedelta(days=1)
        while d.weekday() >= 5:
            d += datetime.timedelta(days=1)
        return d
    for stock_idx in range(3):
        rows = []
        price = 100.0 + stock_idx * 50
        d = start
        for _ in range(300):
            delta = random.uniform(-0.02, 0.02)
            new_price = round(price * (1 + delta), 2)
            open_ = round(price + random.uniform(-0.5, 0.5), 2)
            high = round(max(open_, new_price) + random.uniform(0, 0.5), 2)
            low = round(min(open_, new_price) - random.uniform(0, 0.5), 2)
            vol = random.randint(1_000_000, 5_000_000)
            rows.append([d.isoformat(), open_, high, low, new_price, vol])
            price = new_price
            d = next_business_day(d)
        fname = f'sample_data/stock{stock_idx+1}.csv'
        with open(fname, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date','open','high','low','close','volume'])
            writer.writerows(rows)
        print(f"Generated {fname}")

if __name__ == '__main__':
    generate()
