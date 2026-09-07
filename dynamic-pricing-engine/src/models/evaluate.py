from __future__ import annotations
import math
import numpy as np
import pandas as pd


def enforce_quantile_order(p10, p50, p90):
    p10 = np.asarray(p10, dtype=np.float64)
    p50 = np.asarray(p50, dtype=np.float64)
    p90 = np.asarray(p90, dtype=np.float64)
    p50_safe = np.where(np.isnan(p50), 0.0, p50)
    p10_safe = np.where(np.isnan(p10), p50_safe, p10)
    p90_safe = np.where(np.isnan(p90), p50_safe, p90)
    s10 = np.minimum(p10_safe, p50_safe)
    s90 = np.maximum(p90_safe, p50_safe)
    return s10, p50_safe, s90


def pinball_loss(y_true, y_pred, alpha: float) -> float:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    diff = y_true - y_pred
    return float(2.0 * np.mean(np.maximum(alpha * diff, (alpha - 1.0) * diff)))


def mae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)


def r2(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    if ss_tot == 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot
