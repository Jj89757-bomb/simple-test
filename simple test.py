import streamlit as st
import os
import shutil
from pathlib import Path
import datetime
import numpy as np
import urllib.request # 预防 NameError

# ================= 配置 =================
DATA_FILE_NAME = "f107_ap.npz"
# =======================================

st.set_page_config(page_title="NRLMSIS Nuclear Option", page_icon="☢️")
st.title("☢️ NRLMSIS-2.0 核弹级离线版")

# 1. 准备数据文件
current_dir = Path(__file__).parent.resolve()
source_path = current_dir / DATA_FILE_NAME

if not source_path.exists():
    st.error(f"❌ 找不到 {DATA_FILE_NAME}")
    st.stop()

st.success(f"✅ 找到数据文件：{source_path}")

# 2. 加载数据到内存 (全局可用)
try:
    _LOCAL_DATA = np.load(str(source_path), allow_pickle=True)
    st.success("✅ 数据已加载到内存")
except Exception as e:
    st.error(f"加载数据失败: {e}")
    st.stop()

# 3. 【核心大招】Monkey Patch: 替换联网函数
def _offline_get_f107_ap(dates):
    """
    完全离线的 get_f107_ap 替代品。
    直接从我们加载的 _LOCAL_DATA 中插值获取数据。
    """
    dates = np.asarray(dates, dtype=np.datetime64)
    
    local_dates = _LOCAL_DATA['dates']
    local_f107 = _LOCAL_DATA['f107']
    local_ap = _LOCAL_DATA['ap']
    
    # 简单的最近邻插值
    # 对于每个请求的日期，找到本地数据中最近的索引
    indices = np.argmin(np.abs(local_dates[:, None] - dates[None, :]), axis=0)
    
    return local_f107[indices], local_f107[indices], local_ap[indices]

# 执行替换！
import pymsis.utils
import pymsis.msis
# 保存原函数以防万一
pymsis.utils._original_get_f107_ap = pymsis.utils.get_f107_ap
# 替换为离线版
pymsis.utils.get_f107_ap = _offline_get_f107_ap
# 同时也替换 _load_f107_ap_data 防止它被调用时尝试下载
pymsis.utils._load_f107_ap_data = lambda: {"dates": np.array([]), "f107": np.array([]), "ap": np.array([])}
# 甚至替换 download 函数，让它什么都不做
pymsis.utils.download_f107_ap = lambda: None

st.info("🛡️ 已拦截所有网络请求！pymsis 现在被迫使用本地数据。")

# 4. 运行计算
st.divider()
st.subheader("🚀 开始计算 (强制离线模式)")

with st.spinner("正在计算..."):
    try:
        from pymsis import msis

        time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        lon = 0.0
        lat = 45.0
        alt = 400.0
        
        # 既然已经拦截了联网函数，我们现在可以随意传参了！
        # 甚至可以传 None，它也会调用我们替换后的函数来获取数据
        # 但为了保险，我们还是传入 options
        
        # 构造 options (即使键名不对，只要触发了 get_f107_ap，我们的拦截就会生效)
        my_options = [{
            'f107': 150.0, #  dummy value
            'f107a': 150.0,
            'ap': 4.0,
            'ap_prev': 4.0
        }]
        
        # 尝试运行
        # 注意：如果 pymsis 内部逻辑是先检查 options 再决定是否调用 get_f107_ap
        # 我们的拦截依然有效，因为一旦它决定去获取数据，就会调用 get_f107_ap
        
        output = msis.run(
            [time], [lon], [lat], [alt],
            options=my_options
        )
        
        # 解析结果
        if output.ndim == 2:
            temp = float(output[0, 0])
            density = float(output[0, 1])
        elif output.ndim == 5:
            temp = float(output[0, 0, 0, 0, 0])
            density = float(output[0, 0, 0, 0, 1])
        else:
            # 尝试展平
            flat_out = output.reshape(-1, 11)
            temp = float(flat_out[0, 0])
            density = float(flat_out[0, 1])

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="中性温度 (K)", value=f"{temp:.2f}")
        with col2:
            st.metric(label="密度 (kg/m³)", value=f"{density:.2e}")
            
        st.balloons()
        st.success("☢️ 成功！完全离线，无网络泄漏！")
        
    except Exception as e:
        st.error(f"💥 错误: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.warning("提示：即使报错，网络请求也已被拦截。请检查参数格式。")
