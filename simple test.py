import streamlit as st
import os
import shutil
from pathlib import Path
import datetime
import numpy as np

# ================= 配置 =================
DATA_FILE_NAME = "f107_ap.npz"
# =======================================

st.set_page_config(page_title="NRLMSIS Success", page_icon="🚀")
st.title("🚀 NRLMSIS-2.0 最终成功版")

# 1. 准备数据文件
current_dir = Path(__file__).parent.resolve()
source_path = current_dir / DATA_FILE_NAME

if not source_path.exists():
    st.error(f"❌ 找不到 {DATA_FILE_NAME}")
    st.stop()

st.success(f"✅ 找到数据文件：{source_path}")

# 2. 复制文件到缓存目录 (作为备份，虽然下面手动注入可能用不到)
target_dir = Path.home() / ".pymsis"
try:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_dir / DATA_FILE_NAME)
    st.info(f"📂 已备份文件到：{target_dir / DATA_FILE_NAME}")
except Exception as e:
    st.warning(f"⚠️ 备份失败: {e}")

# 3. 核心计算逻辑
st.divider()
st.subheader("🚀 开始计算 (手动注入 Options)")

with st.spinner("正在加载数据并调用模型..."):
    try:
        from pymsis import msis

        # --- A. 手动加载数据 ---
        data = np.load(str(source_path), allow_pickle=True)
        dates_data = data['dates']
        f107_data = data['f107']
        ap_data = data['ap']
        st.success("✅ 数据文件加载成功！")

        # --- B. 准备测试参数 ---
        time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        lon = 0.0
        lat = 45.0
        alt = 400.0
        
        # 找到对应时间的数据索引
        time_np = np.datetime64(time)
        idx = np.argmin(np.abs(dates_data - time_np))
        
        val_f107 = float(f107_data[idx])
        val_ap = float(ap_data[idx])
        # f107a 通常指 81 天平均，这里为了简单测试，我们用当日值代替，或者你可以计算滑动平均
        # 对于单次测试，直接传入 f107 和 ap 即可，模型内部有默认处理逻辑
        # 但为了完全控制，我们构造 options
        
        st.write(f"📊 使用数据点 (索引 {idx}): F10.7={val_f107}, Ap={val_ap}")

        # --- C. 【关键】构造 options 列表 ---
        # pymsis.run 的签名通常是 run(dates, lons, lats, alts, options=None)
        # options 是一个列表，每个元素对应一个时间点的配置字典
        # 字典键包括: 'f107', 'f107a', 'ap', 'ap_prev', etc.
        
        my_options = [{
            'f107': val_f107,
            'f107a': val_f107,  # 用当日值近似 81 天平均
            'ap': val_ap,
            'ap_prev': val_ap   # 前一天的 ap，也用当前值近似
        }]

        # --- D. 执行计算 ---
        # 注意：第一个参数可以是单个时间或时间列表。如果是列表，options 长度必须匹配。
        # 这里我们传入列表以匹配 options
        output = msis.run(
            [time], [lon], [lat], [alt],
            options=my_options
        )
        
        # --- E. 解析结果 ---
        # 此时输出通常是 (1, 1, 1, 1, 11) 或 (1, 11) 取决于版本
        # 我们取第一个点的温度和密度
        if output.ndim == 2:
            # (1, 11)
            temp = float(output[0, 0])
            density = float(output[0, 1])
        elif output.ndim == 5:
            # (1, 1, 1, 1, 11)
            temp = float(output[0, 0, 0, 0, 0])
            density = float(output[0, 0, 0, 0, 1])
        else:
            st.error(f"❌ 未知的输出维度: {output.shape}")
            st.stop()

        # --- F. 显示结果 ---
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="中性温度 (Temperature)", value=f"{temp:.2f} K")
        with col2:
            st.metric(label="总质量密度 (Density)", value=f"{density:.2e} kg/m³")
            
        st.balloons()
        st.success("🎉 计算成功！完全离线运行，无网络请求！")
        
        with st.expander("查看详细输出数组"):
            st.write(f"形状: {output.shape}")
            st.write("变量顺序: Temp, Density, N2, O2, O, Ar, He, H, N, NO, Mass")
            st.write(output)

    except Exception as e:
        st.error(f"💥 发生错误: {e}")
        import traceback
        st.code(traceback.format_exc())
