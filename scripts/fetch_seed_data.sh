#!/usr/bin/env bash
# Flipkart product dump, used to train the price model.
#
# PromptCloud, CC BY SA 4.0. Attribute it.
#
# 20,000 rows, 99.6 percent carrying a price, of which roughly 1,700 are craft
# adjacent. Crawled in 2016, so prices are a decade stale. We use it for
# STRUCTURE, meaning how material and category move price relative to each
# other, and layer a small current price table on top for the crafts we pitch.
set -euo pipefail

DEST="data/seed/flipkart.csv"
URL="https://raw.githubusercontent.com/VishalS-HK/product-recommendation-system-BERT/main/data/flipkart_com-ecommerce_sample.csv"

mkdir -p data/seed
echo "Downloading Flipkart sample, about 38 MB"
curl -fSL "$URL" -o "$DEST"
echo "Saved to $DEST"
wc -l "$DEST"
