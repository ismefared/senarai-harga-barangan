import pandas as pd
import json
from datetime import datetime, timedelta

BULAN_SEMASA = datetime.now().strftime("%Y-%m")

# Item yang disasar — item_code SAHIH, disahkan daripada lookup_item.parquet
# (Beras & Ubi Kentang guna PURATA merentas beberapa item_code kerana tiada
# satu kod "generik" bagi kategori itu — lihat nota reka bentuk dalam chat)
ITEM_DISASAR = {
    "Beras": {
        "item_code": [992, 1445, 1581, 1582, 1832, 1902, 1951, 2004],  # jenama tempatan SST5%
        "unit": "10kg",
    },
    "Minyak Masak": {
        "item_code": [918],  # MINYAK MASAK PAKET (PELBAGAI JENAMA) 1kg
        "unit": "1kg",
    },
    "Ayam": {
        "item_code": [1],  # AYAM BERSIH - STANDARD 1kg
        "unit": "1kg",
    },
    "Telur Gred A": {
        "item_code": [118],  # TELUR AYAM GRED A (65.0-69.9gm) 10 biji
        "unit": "10 biji",
    },
    "Ubi Kentang": {
        "item_code": [160, 861, 1131],  # Russet, Holland, Import China
        "unit": "1kg",
    },
}


def muat_lookup():
    """Rujukan sahaja — sudah dijalankan sekali untuk cari item_code 5 barang
    semasa (lihat ITEM_DISASAR di atas). Guna semula ini bila nak tambah
    barang baharu pada masa hadapan."""
    lookup_item = pd.read_parquet(
        "https://storage.data.gov.my/pricecatcher/lookup_item.parquet"
    )
    return lookup_item


def cari_kod_item(lookup_item, kata_kunci):
    """Cari item_code berdasarkan nama — guna bila nak tambah barang baharu."""
    return lookup_item[lookup_item["item"].str.contains(kata_kunci, case=False, na=False)]


def muat_harga_bulan(bulan):
    url = f"https://storage.data.gov.my/pricecatcher/pricecatcher_{bulan}.parquet"
    return pd.read_parquet(url)


def proses_trend():
    hasil = []
    # ambil 6 bulan kebelakang supaya sparkline ada konteks
    bulan_senarai = [
        (datetime.now().replace(day=1) - timedelta(days=30 * i)).strftime("%Y-%m")
        for i in range(5, -1, -1)
    ]

    df_semua = pd.concat(
        [muat_harga_bulan(b) for b in bulan_senarai if b], ignore_index=True
    )

    for nama, info in ITEM_DISASAR.items():
        # subset ikut senarai item_code (sokong purata merentas >1 kod)
        subset = df_semua[df_semua["item_code"].isin(info["item_code"])]

        # purata harian dahulu (elak jenama dgn lebih banyak premis mendominasi),
        # kemudian purata bulanan daripada purata harian itu
        purata_harian = subset.groupby("date")["price"].mean()
        purata_harian.index = pd.to_datetime(purata_harian.index).strftime("%Y-%m")
        purata_bulanan = purata_harian.groupby(purata_harian.index).mean().round(2)

        siri = purata_bulanan.reindex(bulan_senarai).ffill().bfill().tolist()
        hasil.append({
            "nama": nama,
            "unit": info["unit"],
            "data": siri,
        })

    return {
        "kemaskini_terakhir": datetime.now().isoformat(),
        "sumber": "KPDN PriceCatcher (data.gov.my), purata bulanan",
        "trend": hasil,
    }


if __name__ == "__main__":
    output = proses_trend()
    with open("data/trend.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Selesai:", output["kemaskini_terakhir"])
