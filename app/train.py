import os
import json
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score
import joblib

# Metadata
NAME = "Shanik Hubert"
ROLL_NO = "2022BCS0012"

# Paths (MATCH JENKINS PIPELINE)
DATA_PATH = "data/winequality-red.csv"
OUTPUT_DIR = "app/artifacts"
MODEL_PATH = os.path.join(OUTPUT_DIR, "model.pkl")
METRICS_PATH = os.path.join(OUTPUT_DIR, "metrics.json")


def train_model(model, experiment_name, threshold=0.5):
    df = pd.read_csv(DATA_PATH, sep=";")
    y = df["quality"]
    X = df.drop(columns=["quality"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Regression metrics
    mse = mean_squared_error(y_test, y_pred)
    rmse = mse ** 0.5
    r2 = r2_score(y_test, y_pred)

    # Optional tolerance accuracy
    correct = (abs(y_pred - y_test) < threshold).sum()
    accuracy = correct / len(y_test)

    metrics = {
        "name": NAME,
        "roll_no": ROLL_NO,
        "experiment": experiment_name,
        "r2": float(r2),
        "rmse": float(rmse),
        "accuracy": float(accuracy)
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    joblib.dump(model, MODEL_PATH)

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=4)

    print(metrics)


if __name__ == "__main__":

    model = DecisionTreeRegressor(
        max_depth=15,
        min_samples_leaf=5,
        random_state=42
    )

    experiment_name = type(model).__name__

    train_model(model, experiment_name)
