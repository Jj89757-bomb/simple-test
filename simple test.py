import streamlit as st
import os
import shutil
from pathlib import Path
import datetime
import numpy as np

# ================= 配置 =================
DATA_FILE_NAME = "f107_ap.npz"
# =======================================

st.set_page_config(page_title="NRLMSIS Simple Test", page_icon="🌍")
st.title("🌍 NRLMSIS-2.0 简单测试 (修复版)")
st.markdown("此应用演示如何在 Streamlit Cloud 上离线运行 `pymsis`。")

# 1. 准备数据文件 (核心步骤：复制文件到缓存目录)
current_dir = Path(__file__).parent
source_path = current_dir / DATA_FILE_NAME
target_dir = Path.home() / ".pymsis"
target_path = target_dir / DATA_FILE_NAME

if not source_path.exists():
    st.error(f"❌ 错误：未在仓库中找到 `{DATA_FILE_NAME}`。\n请确保已将该文件上传到 GitHub，并与本脚本在同一目录。")
    st.stop()

try:
    target_dir.mkdir(exist_ok=True)
    if not target_path.exists() or source_path.stat().st_mtime > target_path.stat().st_mtime:
        shutil.copy(source_path, target_path)
        st.success(f"✅ 数据文件已部署到系统缓存：{target_path}")
    else:
        st.info(f"ℹ️ 数据文件已存在且为最新。")
except Exception as e:
    st.warning(f"⚠️ 文件复制遇到小问题：{e}，将继续尝试运行...")

# 2. 运行模型
st.divider()
st.subheader("🚀 开始计算")

with st.spinner("正在调用 NRLMSIS-2.0 模型..."):
    try:
        from pymsis import msis

        # 测试参数：2023年1月1日，经度0，纬度45，高度400km
        time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        lon = 0.0
        lat = 45.0
        alt = 400.0

        # 执行计算
        output = msis.run(time, lon, lat, alt)

        # --- 🔧 核心修复：自适应处理数组维度 ---
        # pymsis 可能返回 2D (点数, 变量) 或 5D (时间, 经度, 纬度, 高度, 变量)
        if output.ndim == 2:
            # 2D 情况：直接取第一行 (第一个点) 的前两个变量 (温度, 密度)
            # 形状: (1, 11) -> 取 [0, 0] 和 [0, 1]
            temp = float(output[0, 0])
            density = float(output[0, 1])
            shape_info = f"2D Array: {output.shape} (点数, 变量)"
        elif output.ndim == 5:
            # 5D 情况：取 [0, 0, 0, 0, 0] 和 [0, 0, 0, 0, 1]
            temp = float(output[0, 0, 0, 0, 0])
            density = float(output[0, 0, 0, 0, 1])
            shape_info = f"5D Array: {output.shape} (时间, 经度, 纬度, 高度, 变量)"
        else:
            st.error(f"❌ 未知的数据维度：{output.ndim}。无法解析结果。")
            st.stop()
        # -----------------------------------

        # 显示结果
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="中性温度 (Temperature)",
                value=f"{temp:.2f} K",
                delta=None
            )
        with col2:
            st.metric(
                label="总质量密度 (Density)",
                value=f"{density:.2e} kg/m³",
                delta=None
            )

        st.success("🎉 计算成功！PyMSIS 已在当前环境正常运行。")

        with st.expander("查看原始数据数组信息"):
            st.write(f"**输出形状**: {shape_info}")
            st.write(f"**变量列表**: ['Temp', 'Density', 'N2', 'O2', 'O', 'Ar', 'He', 'H', 'N', 'NO', 'Mass']")
            st.write("前 5 行数据预览:")
            st.write(output[:5] if output.ndim == 2 else output.flatten()[:10])

    except ImportError as ie:
        st.error(f"❌ 导入错误：{ie}\n请检查 `requirements.txt` 是否包含 `pymsis`。")
    except Exception as e:
        st.error(f"💥 运行时错误：{e}")
        import traceback

        st.code(traceback.format_exc())
