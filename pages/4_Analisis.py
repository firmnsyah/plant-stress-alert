import plotly.express as px
import pandas as pd
import streamlit as st

from app import get_db
from core.stats import anova_tukey, pca

db = get_db()
st.header("Analisis")
frame = db.list_observations()
if frame.empty:
    st.info("Belum ada observasi.")
    st.stop()
if "stress_index" in frame and frame["stress_index"].notna().any():
    st.plotly_chart(px.line(frame, x="observed_at", y="stress_index", color="treatment",
                            markers=True, title="Stress Index terhadap waktu"),
                    width="stretch")
metric = st.selectbox("Variabel statistik", ["stress_index", "norm_bio", "norm_temp", "norm_color", "norm_el"])
stat_frame = frame.dropna(subset=[metric, "treatment"])
if stat_frame["treatment"].nunique() >= 2:
    try:
        result = anova_tukey(stat_frame, metric)
        st.subheader("ANOVA dan Tukey")
        st.metric("F-statistic", f"{result['f_statistic']:.4f}")
        st.metric("p-value", f"{result['p_value']:.6f}")
        if result["tukey"] is not None:
            st.text(result["tukey"])
    except ValueError as exc:
        st.warning(str(exc))
norm_columns = ["norm_bio", "norm_temp", "norm_color", "norm_el"]
if all(column in frame for column in norm_columns):
    pca_frame = frame.dropna(subset=norm_columns)
    if len(pca_frame) >= 2:
        result = pca(pca_frame, norm_columns)
        scores = pd.DataFrame(result["scores"], columns=["PC1", "PC2"][:result["scores"].shape[1]])
        scores["treatment"] = pca_frame["treatment"].to_numpy()
        st.subheader("PCA")
        st.caption("Varians terjelaskan: " + ", ".join(f"{value:.1%}" for value in result["explained_variance_ratio"]))
        st.plotly_chart(px.scatter(scores, x="PC1", y="PC2" if "PC2" in scores else "PC1",
                                   color="treatment", title="PCA fingerprint"),
                        width="stretch")
st.subheader("Ringkasan per perlakuan")
st.dataframe(frame.groupby("treatment", as_index=False).agg(
    observasi=("id", "count"), rata_stress=("stress_index", "mean")),
    width="stretch", hide_index=True)
