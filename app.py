import streamlit as st
import pandas as pd
import zipfile
import io
import re

# ==========================================
# 页面基础配置
# ==========================================
st.set_page_config(page_title="一站式 CSV/Excel 处理工具", layout="wide")
st.title("🧰 一站式表格合并、校对与拆分工具")

# ==========================================
# 核心通用函数
# ==========================================
def smart_read_file(uploaded_file):
    """尝试读取 CSV 或 Excel 文件，自动处理编码问题"""
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.csv'):
        try:
            return pd.read_csv(uploaded_file, encoding='utf-8')
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding='gbk')
    elif file_name.endswith(('.xls', '.xlsx')):
        # 这里就是之前报错的地方，有了 requirements.txt 里的 openpyxl 就不报错了
        return pd.read_excel(uploaded_file)
    return None

def sanitize_filename(filename):
    """清理文件名中的非法字符，防止保存或打包时报错"""
    filename = str(filename)
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def display_data_dashboard(df, title="📊 数据简易看板 (处理结果体检)"):
    """为传入的表格生成一个直观的统计看板"""
    st.divider()
    st.subheader(title)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="总行数 (Rows)", value=f"{len(df):,}")
    col2.metric(label="总列数 (Columns)", value=f"{len(df.columns):,}")
    col3.metric(label="缺失值总计 (Nulls)", value=f"{df.isna().sum().sum():,}")
    col4.metric(label="完全重复行 (Duplicates)", value=f"{df.duplicated().sum():,}")
    
    with st.expander("👁️ 点击查看：各列字段详细健康状况"):
        summary_df = pd.DataFrame({
            "数据类型": df.dtypes.astype(str),
            "非空值数量": df.notna().sum(),
            "缺失值数量": df.isna().sum(),
            "唯一值数量 (去重后)": df.nunique()
        })
        st.dataframe(summary_df, use_container_width=True)

def generate_joint_key(df, columns):
    """根据多列生成联合比对键，防范空值并统一格式"""
    return df[columns].fillna('').astype(str).apply(lambda x: '_|_'.join(x.str.strip()), axis=1)

# ==========================================
# 创建 5 个选项卡
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📁 批量合并", 
    "🔍 两表校对 (找重复/差异)", 
    "🗂️ 批量按条件提取", 
    "✂️ 单表分类拆分", 
    "🛑 批量黑名单剔除"
])

# ==========================================
# 选项卡 1：批量合并
# ==========================================
with tab1:
    st.header("批量合并表格文件")
    uploaded_files = st.file_uploader("拖拽多个 CSV/Excel 文件到这里", type=["csv", "xlsx", "xls"], accept_multiple_files=True, key="merge_uploader")
    
    if uploaded_files:
        file_names = [f.name for f in uploaded_files]
        selected_files = st.multiselect("✅ 请确认要参与合并的文件（取消勾选以剔除错传文件）：", options=file_names, default=file_names)
        valid_files = [f for f in uploaded_files if f.name in selected_files]
        
        new_file_name = st.text_input("📝 自定义导出文件名（需包含 .csv 后缀）：", value="批量合并结果.csv", key="tab1_name")
        
        if st.button("开始合并", type="primary", key="merge_btn") and valid_files:
            dfs = [smart_read_file(f) for f in valid_files]
            merged_df = pd.concat(dfs, ignore_index=True)
            st.success(f"✅ 成功合并了 {len(valid_files)} 个文件！")
            display_data_dashboard(merged_df, title="📊 合并结果看板")
            
            st.write("✏️ **数据预览与编辑（你可以直接双击下方单元格修改内容，修改后下载生效）：**")
            edited_df = st.data_editor(merged_df, use_container_width=True, num_rows="dynamic")
            
            csv_data = edited_df.to_csv(index=False).encode('utf-8-sig') 
            st.download_button(label="📥 下载最终合并表格", data=csv_data, file_name=new_file_name, mime="text/csv")

# ==========================================
# 选项卡 2：两表校对 (为你优化了文案，明确“提取重复数据”功能)
# ==========================================
with tab2:
    st.header("校对两批数据文件")
    col1, col2 = st.columns(2)
    with col1:
        file_a = st.file_uploader("上传 表格 A (基准表)", type=["csv", "xlsx"], key="file_a")
    with col2:
        file_b = st.file_uploader("上传 表格 B (比对表)", type=["csv", "xlsx"], key="file_b")
        
    if file_a and file_b:
        df_a = smart_read_file(file_a)
        df_b = smart_read_file(file_b)
        
        st.subheader("⚙️ 设置联合校对规则")
        col3, col4 = st.columns(2)
        with col3:
            key_a = st.multiselect("选择【表格 A】用于比对的列（支持多选作联合主键）：", df_a.columns, default=[df_a.columns[0]])
        with col4:
            key_b = st.multiselect("选择【表格 B】用于比对的列（需与左侧列顺序及数量一致）：", df_b.columns, default=[df_b.columns[0]])
            
        # 这里的文案为你做了专门的优化，功能其实就是提取你想要的重复项
        compare_mode = st.radio("你想查看什么结果？", [
            "👉 找出两表共有的【重复项】(提取重复数据生成新表)", 
            "找出【表格 A】独有的【差异项】", 
            "找出【表格 B】独有的【差异项】"
        ])
        compare_name = st.text_input("📝 自定义导出文件名（需包含 .csv 后缀）：", value="两表提取结果.csv", key="tab2_name")
        
        if st.button("开始自动校对", type="primary", key="compare_btn"):
            if len(key_a) != len(key_b) or len(key_a) == 0:
                st.error("❌ 错误：两表选择的比对列数量必须完全一致且不能为空！")
            else:
                df_a_keys = generate_joint_key(df_a, key_a)
                df_b_keys = generate_joint_key(df_b, key_b)
                
                if compare_mode == "👉 找出两表共有的【重复项】(提取重复数据生成新表)":
                    result_df = df_a[df_a_keys.isin(df_b_keys)]
                elif compare_mode == "找出【表格 A】独有的【差异项】":
                    result_df = df_a[~df_a_keys.isin(df_b_keys)]
                else:
                    result_df = df_b[~df_b_keys.isin(df_a_keys)]
                    
                if not result_df.empty:
                    st.success(f"🔍 查验完成！找到 {len(result_df)} 条符合条件的数据。")
                    display_data_dashboard(result_df, title="📊 校对提取结果看板")
                    
                    st.write("✏️ **数据编辑区（可直接修改结果后再导出）：**")
                    edited_result = st.data_editor(result_df, use_container_width=True, num_rows="dynamic")
                    
                    csv_result = edited_result.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(label="📥 下载提取结果", data=csv_result, file_name=compare_name, mime="text/csv")
                else:
                    st.info("🤷‍♂️ 根据当前规则，没有找到符合条件的数据。")

# ==========================================
# 选项卡 3：批量按条件提取
# ==========================================
with tab3:
    st.header("批量按条件提取数据")
    extract_files = st.file_uploader("拖拽多个 CSV/Excel 文件到这里", type=["csv", "xlsx"], accept_multiple_files=True, key="extract_uploader")
    
    if extract_files:
        e_file_names = [f.name for f in extract_files]
        e_selected_files = st.multiselect("✅ 确认提取范围（取消勾选以排除）：", options=e_file_names, default=e_file_names)
        valid_extract_files = [f for f in extract_files if f.name in e_selected_files]

        if valid_extract_files:
            first_file_df = smart_read_file(valid_extract_files[0])
            columns = first_file_df.columns.tolist()
            valid_extract_files[0].seek(0)
            
            col5, col6 = st.columns(2)
            with col5:
                filter_col = st.selectbox("请选择要筛选的列：", columns, key="filter_col")
            with col6:
                filter_value = st.text_input(f"请输入【{filter_col}】中要提取的具体内容：")
            
            extract_name = st.text_input("📝 自定义导出文件名：", value="按条件提取结果.csv", key="tab3_name")
                
            if st.button("开始批量提取", type="primary", key="extract_btn"):
                if not filter_value:
                    st.warning("⚠️ 请先输入提取内容！")
                else:
                    extracted_dfs = []
                    for file in valid_extract_files:
                        df = smart_read_file(file)
                        if filter_col in df.columns:
                            df[filter_col] = df[filter_col].astype(str).str.strip()
                            matched_df = df[df[filter_col] == str(filter_value).strip()]
                            if not matched_df.empty:
                                extracted_dfs.append(matched_df)
                                
                    if extracted_dfs:
                        final_df = pd.concat(extracted_dfs, ignore_index=True)
                        st.success("✅ 提取完成！")
                        display_data_dashboard(final_df, title="📊 提取结果看板")
                        
                        st.write("✏️ **数据编辑区（修改后下载）：**")
                        edited_final = st.data_editor(final_df, use_container_width=True, num_rows="dynamic")
                        
                        csv_extract = edited_final.to_csv(index=False).encode('utf-8-sig')
                        final_name = extract_name if extract_name != "按条件提取结果.csv" else f"提取结果_{sanitize_filename(filter_value)}.csv"
                        st.download_button("📥 下载提取结果", data=csv_extract, file_name=final_name, mime="text/csv")
                    else:
                        st.info("🤷‍♂️ 未找到匹配数据。")

# ==========================================
# 选项卡 4：单表分类拆分
# ==========================================
with tab4:
    st.header("按指定列将表格拆分为多个新文件")
    split_file = st.file_uploader("📁 上传要拆分的表格 (CSV / Excel)", type=["csv", "xlsx", "xls"], key="split_uploader")
    
    if split_file:
        split_df = smart_read_file(split_file)
        if split_df is not None:
            display_data_dashboard(split_df, title="📊 上传数据的原始体检")
            
            columns = split_df.columns.tolist()
            target_column = st.selectbox("请选择分类依据的列：", columns, key="split_col")
            split_name = st.text_input("📝 自定义导出的压缩包名称：", value=f"拆分结果_{target_column}.zip", key="tab4_name")
            
            if st.button("✂️ 开始分类拆分", type="primary"):
                grouped = split_df.groupby(split_df[target_column].fillna("未分类"))
                zip_buffer = io.BytesIO()
                file_count = 0
                
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for category_name, group_data in grouped:
                        safe_name = sanitize_filename(category_name)
                        csv_data = group_data.to_csv(index=False).encode('utf-8-sig')
                        zip_file.writestr(f"{safe_name}.csv", csv_data)
                        file_count += 1
                
                st.success(f"🎉 拆分成功！共拆分出了 {file_count} 个表格文件。")
                st.download_button("📥 下载所有拆分后的文件 (ZIP 压缩包)", data=zip_buffer.getvalue(), file_name=split_name, mime="application/zip", type="primary")

# ==========================================
# 选项卡 5：批量黑名单剔除
# ==========================================
with tab5:
    st.header("批量黑名单剔除 (多表联合去重)")
    st.write("将一个【目标底表】与多个【黑名单表】进行比对，自动剔除底表里曾在黑名单中出现过的数据。")
    
    col7, col8 = st.columns(2)
    with col7:
        target_file = st.file_uploader("🎯 1. 上传【目标底表】", type=["csv", "xlsx"], key="target_uploader")
    with col8:
        blacklist_files = st.file_uploader("🛑 2. 批量上传【黑名单表】", type=["csv", "xlsx"], accept_multiple_files=True, key="blacklist_uploader")
        
    if target_file and blacklist_files:
        bl_file_names = [f.name for f in blacklist_files]
        bl_selected_files = st.multiselect("✅ 确认启用的黑名单文件：", options=bl_file_names, default=bl_file_names)
        valid_blacklist_files = [f for f in blacklist_files if f.name in bl_selected_files]
        
        if target_file and valid_blacklist_files:
            target_df = smart_read_file(target_file)
            first_bl_df = smart_read_file(valid_blacklist_files[0])
            valid_blacklist_files[0].seek(0)
            
            st.subheader("⚙️ 设置联合剔除规则")
            col9, col10 = st.columns(2)
            with col9:
                target_key = st.multiselect("选择【目标底表】核对列（支持多选作联合主键）：", target_df.columns, default=[target_df.columns[0]], key="target_key")
            with col10:
                bl_key = st.multiselect("选择【黑名单表】核对列（数量需与左侧一致）：", first_bl_df.columns, default=[first_bl_df.columns[0]], key="bl_key")
            
            original_name = str(target_file.name).rsplit('.', 1)[0]
            clean_name = st.text_input("📝 自定义清洗后的导出文件名：", value=f"{original_name}_去重.csv", key="tab5_name")
                
            if st.button("🚀 开始剔除清洗", type="primary", key="clean_btn"):
                if len(target_key) != len(bl_key) or len(target_key) == 0:
                    st.error("❌ 错误：比对列数量必须完全一致且不能为空！")
                else:
                    target_combined_keys = generate_joint_key(target_df, target_key)
                    
                    all_blacklist_items = set()
                    total_bl_rows = 0
                    
                    for bl_file in valid_blacklist_files:
                        bl_df = smart_read_file(bl_file)
                        if all(k in bl_df.columns for k in bl_key):
                            bl_combined_keys = generate_joint_key(bl_df, bl_key)
                            all_blacklist_items.update(bl_combined_keys.tolist())
                            total_bl_rows += len(bl_df)
                    
                    original_len = len(target_df)
                    cleaned_target_df = target_df[~target_combined_keys.isin(all_blacklist_items)]
                    removed_count = original_len - len(cleaned_target_df)
                    
                    st.success("✅ 清洗完成！")
                    st.info(f"📊 摘要：底表原始 {original_len} 行，匹配并剔除 **{removed_count}** 行，最终剩余 **{len(cleaned_target_df)}** 行。")
                    
                    display_data_dashboard(cleaned_target_df, title="📊 清洗后的干净数据看板")
                    
                    st.write("✏️ **数据编辑区（直接对清洗后的结果做最后修改）：**")
                    edited_clean_df = st.data_editor(cleaned_target_df, use_container_width=True, num_rows="dynamic")
                    
                    if not edited_clean_df.empty:
                        csv_clean = edited_clean_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(label="📥 下载清洗后的新表格", data=csv_clean, file_name=clean_name, mime="text/csv")