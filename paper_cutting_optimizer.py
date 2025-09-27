# paper_cutting_optimizer_pro.py - 实用生产版本
import streamlit as st
import pandas as pd
import numpy as np
from itertools import product, combinations
from collections import Counter
import time

# 设置页面配置
st.set_page_config(
    page_title="恒丰纸业 - 实用套切优化系统",
    page_icon="🏭", 
    layout="wide",
    initial_sidebar_state="expanded"
)

class PracticalCuttingOptimizer:
    def __init__(self, master_width=5480, min_utilization=0.85, max_patterns=3, allow_waste=0.05):
        """
        实用套切优化器
        
        Args:
            master_width: 母卷宽度
            min_utilization: 最低利用率阈值
            max_patterns: 最大允许的方案种类数（减少换刀次数）
            allow_waste: 允许的损耗比例（5%）
        """
        self.master_width = master_width
        self.min_utilization = min_utilization
        self.max_patterns = max_patterns
        self.allow_waste = allow_waste
        self.min_width = master_width * min_utilization
    
    def generate_efficient_patterns(self, widths):
        """生成高效切割方案，优先考虑高利用率和简单组合"""
        patterns = []
        
        # 优先考虑2-3种规格的组合（生产操作简单）
        for num_pieces in range(2, 4):  # 2-3种规格
            for combo in product(widths, repeat=num_pieces):
                total_width = sum(combo)
                
                if total_width <= self.master_width and total_width >= self.min_width:
                    pattern_counter = Counter(combo)
                    pattern_desc = '+'.join(f"{count}×{width}" for width, count in pattern_counter.items())
                    
                    utilization = total_width / self.master_width
                    patterns.append({
                        'description': pattern_desc,
                        'total_width': total_width,
                        'utilization': utilization,
                        'composition': dict(pattern_counter),
                        'complexity': len(pattern_counter)  # 组合复杂度
                    })
        
        # 按利用率降序排序，简单组合优先
        patterns.sort(key=lambda x: (-x['utilization'], x['complexity']))
        return patterns
    
    def evaluate_pattern_score(self, pattern, remaining_orders, used_patterns_count):
        """评估方案得分，综合考虑利用率、生产效率和换刀成本"""
        base_score = pattern['utilization']  # 基础分：利用率
        
        # 生产效率奖励：方案能运行的次数越多越好
        max_runs = float('inf')
        for width, count in pattern['composition'].items():
            if count > 0:
                available = remaining_orders.get(width, 0)
                if available < count:
                    return -1  # 不可行
                max_runs = min(max_runs, available // count)
        
        production_efficiency = min(max_runs / 10, 1.0)  # 运行次数奖励
        base_score += production_efficiency * 0.2
        
        # 换刀成本惩罚：方案种类越多，惩罚越大
        pattern_diversity_penalty = used_patterns_count * 0.1
        base_score -= pattern_diversity_penalty
        
        # 简单组合奖励：2-3种规格的组合更受欢迎
        complexity_bonus = 0
        if pattern['complexity'] == 2:
            complexity_bonus = 0.15  # 双切分奖励
        elif pattern['complexity'] == 3:
            complexity_bonus = 0.1   # 三切分奖励
        
        base_score += complexity_bonus
        
        return base_score, max_runs
    
    def optimize_for_production(self, orders):
        """为实际生产优化的套切算法"""
        start_time = time.time()
        
        widths = list(orders.keys())
        patterns = self.generate_efficient_patterns(widths)
        
        remaining_orders = orders.copy()
        production_plan = []
        used_patterns = set()
        total_coils_used = 0
        
        iteration = 0
        max_iterations = 50
        
        while any(remaining_orders.values()) and iteration < max_iterations:
            iteration += 1
            
            best_pattern = None
            best_score = -1
            best_runs = 0
            
            # 优先考虑已使用的方案类型（减少换刀）
            for pattern in patterns:
                # 检查是否可行
                score, max_runs = self.evaluate_pattern_score(pattern, remaining_orders, len(used_patterns))
                if score < 0:
                    continue
                
                # 如果是新方案类型，需要额外考虑是否值得换刀
                pattern_key = tuple(sorted(pattern['composition'].keys()))
                if pattern_key not in used_patterns and len(used_patterns) >= self.max_patterns:
                    # 已经达到最大方案种类数，新方案需要特别优秀才考虑
                    score *= 0.7  # 惩罚新方案
                
                if score > best_score:
                    best_score = score
                    best_pattern = pattern
                    best_runs = max_runs
            
            if best_pattern is None:
                # 没有找到合适方案，尝试允许超额生产
                for pattern in patterns:
                    max_runs = float('inf')
                    feasible = True
                    
                    for width, count in pattern['composition'].items():
                        if count > 0:
                            available = remaining_orders.get(width, 0)
                            # 允许超额生产（在合理范围内）
                            if available < count:
                                # 计算允许的超额量
                                allow_extra = int(orders[width] * self.allow_waste)
                                if available + allow_extra >= count:
                                    max_runs = min(max_runs, 1)  # 只能运行1次
                                else:
                                    feasible = False
                                    break
                            else:
                                max_runs = min(max_runs, available // count)
                    
                    if feasible and max_runs > 0:
                        pattern_key = tuple(sorted(best_pattern['composition'].keys()))
                        score = best_pattern['utilization']
                        if pattern_key not in used_patterns:
                            score *= 0.8  # 新方案惩罚
                        
                        if score > best_score:
                            best_score = score
                            best_pattern = pattern
                            best_runs = max_runs
                
                if best_pattern is None:
                    break
            
            # 应用最佳方案
            pattern_key = tuple(sorted(best_pattern['composition'].keys()))
            used_patterns.add(pattern_key)
            
            # 确定实际运行次数（考虑生产效率）
            actual_runs = best_runs
            if actual_runs > 20:  # 单方案运行次数不宜过多，避免其他规格等待
                actual_runs = min(actual_runs, 20)
            
            production_plan.append({
                'pattern': best_pattern['description'],
                'runs': actual_runs,
                'utilization': best_pattern['utilization'],
                'composition': best_pattern['composition'],
                'pattern_type': f"方案{len(used_patterns)}"
            })
            
            # 更新剩余订单
            for width, count in best_pattern['composition'].items():
                remaining_orders[width] -= count * actual_runs
            
            total_coils_used += actual_runs
            
            # 移除已完成或超额生产的规格
            remaining_orders = {k: v for k, v in remaining_orders.items() 
                               if v > -int(orders.get(k, 0) * self.allow_waste)}
        
        # 计算废料和利用率
        total_waste = 0
        for plan in production_plan:
            waste_per_coil = self.master_width - plan['utilization'] * self.master_width
            total_waste += waste_per_coil * plan['runs']
        
        utilization_rate = 1 - (total_waste / (total_coils_used * self.master_width)) if total_coils_used > 0 else 0
        
        # 计算实际完成情况
        actual_production = {}
        for width in orders.keys():
            produced = orders[width] - remaining_orders.get(width, 0)
            if produced < 0:  # 超额生产
                produced = orders[width]
            actual_production[width] = produced
        
        return {
            'production_plan': production_plan,
            'total_coils': total_coils_used,
            'total_waste': total_waste,
            'utilization_rate': round(utilization_rate, 4),
            'remaining_orders': remaining_orders,
            'actual_production': actual_production,
            'pattern_types': len(used_patterns),
            'computation_time': round(time.time() - start_time, 2)
        }

def main():
    st.title("🏭 恒丰纸业 - 实用套切优化系统")
    st.markdown("""
    **优化目标**：在保证高利用率的同时，尽量减少换刀次数和生产车数
    - ✅ 优先选择2-3种规格的简单组合
    - ✅ 限制方案种类数，减少换刀次数  
    - ✅ 允许合理损耗，避免过度优化
    - ✅ 平衡单方案运行次数，提高生产效率
    """)
    
    # 侧边栏 - 生产参数设置
    st.sidebar.header("🎯 生产参数设置")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        master_width = st.number_input("母卷宽度 (mm)", value=5480, min_value=1000, max_value=10000)
        min_utilization = st.slider("最低利用率", value=0.88, min_value=0.7, max_value=0.95)
    with col2:
        max_patterns = st.slider("最大方案种类", value=3, min_value=1, max_value=5, 
                               help="限制换刀次数，提高生产效率")
        allow_waste = st.slider("允许损耗率", value=0.03, min_value=0.0, max_value=0.1, 
                              help="允许的超额生产比例")
    
    # 订单输入
    st.header("📋 订单输入")
    
    # 常用订单模板
    template_option = st.selectbox(
        "选择订单模板或手动输入",
        ["手动输入", "模板1: 1810×51, 1715×86, 1860×26", "模板2: 1510×37, 1720×10, 1900×49",
         "模板3: 1810×10, 1660×11", "模板4: 大订单优化"]
    )
    
    templates = {
        "模板1: 1810×51, 1715×86, 1860×26": "1810,51\n1715,86\n1860,26",
        "模板2: 1510×37, 1720×10, 1900×49": "1510,37\n1720,10\n1900,49", 
        "模板3: 1810×10, 1660×11": "1810,10\n1660,11",
        "模板4: 大订单优化": "1600,100\n1700,80\n1800,60\n1900,40"
    }
    
    default_orders = templates.get(template_option, "")
    order_input = st.text_area("订单数据（格式：宽度,数量）", value=default_orders, height=150)
    
    # 解析订单
    orders = {}
    try:
        for line in order_input.strip().split('\n'):
            if line.strip():
                width, quantity = line.strip().split(',')
                orders[int(width)] = int(quantity)
    except:
        st.error("❌ 订单数据格式错误！请使用'宽度,数量'格式，每行一个规格")
        return
    
    if not orders:
        st.warning("⚠️ 请输入订单数据")
        return
    
    # 显示订单摘要
    st.subheader("📊 订单摘要")
    col1, col2 = st.columns(2)
    
    with col1:
        order_df = pd.DataFrame([(w, q) for w, q in orders.items()], 
                              columns=['宽度(mm)', '数量'])
        st.dataframe(order_df, use_container_width=True)
    
    with col2:
        total_pieces = sum(orders.values())
        avg_width = sum(w * q for w, q in orders.items()) / total_pieces
        st.metric("总件数", total_pieces)
        st.metric("平均宽度", f"{avg_width:.0f}mm")
        st.metric("规格数量", len(orders))
    
    # 运行优化
    if st.button("🚀 开始优化计算", type="primary"):
        optimizer = PracticalCuttingOptimizer(
            master_width=master_width,
            min_utilization=min_utilization,
            max_patterns=max_patterns,
            allow_waste=allow_waste
        )
        
        with st.spinner("正在计算最优生产方案..."):
            result = optimizer.optimize_for_production(orders)
        
        # 显示优化结果
        st.header("📈 优化结果")
        
        # 关键指标
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总生产车数", result['total_coils'])
        col2.metric("原料利用率", f"{result['utilization_rate']*100:.1f}%")
        col3.metric("方案种类数", result['pattern_types'])
        col4.metric("计算时间", f"{result['computation_time']}s")
        
        # 生产计划详情
        st.subheader("🔄 生产计划详情")
        
        if result['production_plan']:
            plan_df = pd.DataFrame(result['production_plan'])
            plan_df['利用率%'] = (plan_df['utilization'] * 100).round(1)
            plan_df['方案类型'] = plan_df['pattern_type']
            
            # 按方案类型分组显示
            for pattern_type in plan_df['方案类型'].unique():
                st.write(f"**{pattern_type}**")
                pattern_data = plan_df[plan_df['方案类型'] == pattern_type]
                
                for _, row in pattern_data.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 2])
                    with col1:
                        st.write(f"切割方案: {row['pattern']}")
                    with col2:
                        st.write(f"×{row['runs']}车")
                    with col3:
                        st.write(f"利用率: {row['利用率%']}%")
                
                st.write("---")
            
            # 详细数据表
            with st.expander("查看详细数据"):
                display_df = plan_df[['pattern', 'runs', '利用率%', '方案类型']]
                st.dataframe(display_df, use_container_width=True)
        
        # 生产完成情况
        st.subheader("✅ 生产完成情况")
        
        completion_df = pd.DataFrame([
            (width, orders[width], result['actual_production'][width], 
             result['actual_production'][width] - orders[width])
            for width in orders.keys()
        ], columns=['规格', '订单数量', '实际生产', '差异'])
        
        st.dataframe(completion_df, use_container_width=True)
        
        # 分析超额生产情况
        overproduction = [diff for diff in completion_df['差异'] if diff > 0]
        if overproduction:
            st.info(f"📦 允许超额生产: 最大{max(overproduction)}件，总计{sum(overproduction)}件")
        
        # 生产效率分析
        st.subheader("📊 生产效率分析")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_runs_per_pattern = result['total_coils'] / len(result['production_plan']) if result['production_plan'] else 0
            st.metric("平均单方案运行车数", f"{avg_runs_per_pattern:.1f}")
        
        with col2:
            total_pattern_changes = result['pattern_types'] - 1
            st.metric("预计换刀次数", total_pattern_changes)
        
        with col3:
            efficiency_score = result['utilization_rate'] * 100 - total_pattern_changes * 2
            st.metric("生产效率评分", f"{efficiency_score:.1f}")
        
        # 优化建议
        st.subheader("💡 生产建议")
        
        if result['utilization_rate'] > 0.92 and result['pattern_types'] <= 3:
            st.success("""
            🎉 **优秀方案**：
            - 高利用率 + 少换刀次数
            - 建议按此方案组织生产
            """)
        elif result['utilization_rate'] > 0.88:
            st.info("""
            👍 **良好方案**：
            - 平衡了利用率和生产效率
            - 适合批量生产
            """)
        else:
            st.warning("""
            ⚠️ **待优化方案**：
            - 建议调整参数重新计算
            - 可尝试提高允许损耗率或增加方案种类数
            """)
        
        # 经济效益估算
        st.subheader("💰 经济效益估算")
        
        waste_saving = result['total_waste'] / 1000  # 米
        cost_per_meter = 0.033 * (master_width/1000) * 6000 / 1000  # 元/米
        cost_saving = waste_saving * cost_per_meter
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("预计节约原料", f"{waste_saving:.1f}米")
        with col2:
            st.metric("预计节约成本", f"{cost_saving:.0f}元")
        
        # 下载生产计划
        if result['production_plan']:
            csv = plan_df[['pattern', 'runs', '利用率%', '方案类型']].to_csv(index=False)
            st.download_button(
                label="📥 下载生产计划",
                data=csv,
                file_name=f"恒丰纸业生产计划_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
