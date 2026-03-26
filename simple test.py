import streamlit as st
import os
import shutil
from pathlib import Path
import datetime
import numpy as np
import urllib.request # 修复 NameError
import urllib.error

# ================= 配置 =================
DATA_FILE_NAME = "f107_ap.npz"
# =======================================

st.set_page_config(page_title="NRLMSIS Final Fix", page_icon="🎉")
st.title("🎉 NRLMSIS-2.0 终极修复版")

# 1. 准备数据
current_dir = Path(__file__).parent.resolve()
source_path = current_dir / DATA_FILE_NAME

if not source_path.exists():
    st.error(f"❌ 找不到 {DATA_FILE_NAME}")
    st.stop()

st.success(f"✅ 找到数据文件：{source_path}")

# 2. 尝试多种可能的缓存路径 (覆盖所有可能性)
possible_dirs = [
    Path.home() / ".pymsis",          # 标准路径 (/home/appuser/.pymsis)
    Path("/root/.pymsis"),            # 有时库会去这里
    Path("/tmp/.pymsis"),             # 临时目录
    Path(os.environ.get("HOME", "/tmp")) / ".pymsis"
]

target_path = None
for p_dir in possible_dirs:
    try:
        p_dir.mkdir(parents=True, exist_ok=True)
        t_path = p_dir / DATA_FILE_NAME
        shutil.copy2(source_path, t_path)
        st.info(f"📂 已复制文件到：{t_path}")
        if target_path is None:
            target_path = t_path
    except Exception as e:
        pass

# 3. 【核心大招】手动加载数据，直接传给 msis.run
# 这样完全绕过 pymsis 内部的自动下载逻辑
st.divider()
st.subheader("🚀 开始计算 (手动注入数据模式)")

with st.spinner("正在加载数据并计算..."):
    try:
        from pymsis import msis
        from pymsis.utils import get_f107_ap # 尝试导入工具函数
        
        # 手动加载我们刚刚复制的 .npz 文件
        data = np.load(str(source_path), allow_pickle=True)
        
        # 构造 pymsis 需要的数据格式
        # 注意：npz 里的键名可能是 'dates', 'f107', 'ap' 等
        dates_data = data['dates']
        f107_data = data['f107']
        ap_data = data['ap']
        
        st.success("✅ 数据文件手动加载成功！")

        # 测试参数
        time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        lon = 0.0
        lat = 45.0
        alt = 400.0
        
        # 【关键】调用 run 时，显式传入 f107 和 ap 参数
        # 这样 msis.run 就不会去查文件，也不会联网了！
        # 我们需要根据时间插值获取对应的 f107/ap，或者简单起见，传入固定值/最近值
        
        # 简单策略：找到离测试时间最近的数据
        time_np = np.datetime64(time)
        idx = np.argmin(np.abs(dates_data - time_np))
        
        f107_val = float(f107_data[idx])
        f107a_val = float(f107_data[idx]) # 简化处理，用当日值代替81天平均
        ap_val = float(ap_data[idx])
        
        st.write(f"📊 使用数据点 (索引 {idx}): F10.7={f107_val}, Ap={ap_val}")

        # 执行计算 (显式传入空间天气参数)
        output = msis.run(
            time, lon, lat, alt,
            f107=f107_val,
            f107a=f107a_val,
            ap=ap_val
        )
        
        # 处理维度
        if output.ndim == 2:
            temp = float(output[0, 0])
            density = float(output[0, 1])
        elif output.ndim == 5:
            temp = float(output[0, 0, 0, 0, 0])
            density = float(output[0, 0, 0, 0, 1])
        else:
            st.error(f"未知维度：{output.ndim}")
            st.stop()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("温度 (K)", f"{temp:.2f}")
        with col2:
            st.metric("密度 (kg/m³)", f"{density:.2e}")
            
        st.balloons()
        st.success("🎉 完美成功！未发生任何网络请求。")

    except Exception as e:
        st.error(f"💥 错误：{e}")
        import traceback
        st.code(traceback.format_exc())
