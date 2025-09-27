# paper_cutting_optimizer.py - 修复版本
import streamlit as st
import pandas as pd
import numpy as np
from itertools import product
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
        self.master_width = master_width
        self.min_utilization = min_utilization
        self.max_patterns = max_patterns
        self.allow_waste = allow_waste
        self.min_width = master_width * min_utilization
    
    def generate_efficient_patterns(self, widths):
        """生成高效切割方案，优先考虑高利用率和简单组合"""
        patterns = []
        
        # 生成所有可能的组合（1-4种规格）
        for num_pieces in range(1, 5):
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
        """评估方案得分，返回(score, max_runs)元组"""
        # 首先检查模式是否可行，计算最大运行次数
        max_runs = float('inf')
        for width, count in pattern['composition'].items():
            if count > 0:
                available = remaining_orders.get(width, 0)
                if available < count:
                    # 不可行，返回负分和0运行次数
                    return -1, 0
                max_runs = min(max_runs, available // count)
        
        if max_runs == 0:
            return -1, 0  # 不可行
        
        # 计算得分
        base_score = pattern['utilization']  # 基础分：利用率
        
        # 生产效率奖励：方案能运行的次数越多越好
        production_efficiency = min(max_runs / 10, 1.0)
        base_score += production_efficiency * 0.2
        
        # 换刀成本惩罚：方案种类越多，惩罚越大
        pattern_diversity_penalty = used_patterns_count * 0.1
        base_score -= pattern_diversity_penalty
        
        # 简单组合奖励：2-3种规格的组合更受欢迎
        complexity_bonus = 0
        if pattern['complexity'] == 2:
            complexity_bonus = 0.15
        elif pattern['complexity'] == 3:
            complexity_bonus = 0.1
        
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
        total_waste = 0
        
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
                        pattern_key = tuple(sorted(pattern['composition'].keys()))
                        score = pattern['utilization']
                        if pattern_key not in used_patterns:
                            score *= 0.8  # 新方案惩罚
                        
                        if score > best_score:
                            best_score = score
                            best_pattern = pattern
                            best_runs = max_runs
                
                if best_pattern is None:
                    # 仍然没有找到，使用单一切割完成剩余
                    for width, quantity in list(remaining_orders.items()):
                        if quantity > 0 and width <= self.master_width:
                            # 创建单一切割模式（最后手段）
                            single_utilization = width / self.master_width
                            if single_utilization >= 0.8:  # 只有利用率足够高时才使用
                                single_pattern = {
                                    'description': f"1×{width}",
                                    'total_width': width,
                                    'utilization': single_utilization,
                                    'composition': {width: 1},
                                    'complexity': 1
                                }
                                production_plan.append({
                                    'pattern': single_pattern['description'],
                                    'runs': quantity,
                                    'utilization': single_pattern['utilization'],
                                    'composition': single_pattern['composition'],
                                    'pattern_type': f"单一切割"
                                })
                                total_coils_used += quantity
                                total_waste += (self.master_width - width) * quantity
                                remaining_orders[width] = 0
                    break
            
            # 应用最佳方案
            pattern_key = tuple(sorted(best_pattern['composition'].keys()))
            used_patterns.add(pattern_key)
            
            # 确定实际运行次数（考虑生产效率）
            actual_runs = best_runs
            if actual_runs > 20:  # 单方案运行次数不宜过多
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
                remaining_orders[width] = remaining_orders.get(width, 0) - count * actual_runs
            
            total_coils_used += actual_runs
            waste_per_coil = self.master_width - best_pattern['utilization'] * self.master_width
            total_waste += waste_per_coil * actual_runs
            
            # 移除已完成或超额生产的规格
            remaining_orders = {k: v for k, v in remaining_orders.items() 
                               if v > -int(orders.get(k, 0) * self.allow_waste)}
        
        # 计算实际完成情况
        actual_production = {}
        for width in orders.keys():
            produced = orders[width] - remaining_orders.get(width, 0)
            if produced < 0:  # 超额生产
                produced = orders[width] + abs(produced)  # 实际生产量
            actual_production[width] = produced
        
        utilization_rate = 1 - (total_waste / (total_coils_used * self.master_width)) if total_coils_used > 0 else 0
        
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
        ["手动输入", "模板1: 1810×51, 1715×86, 1860×26", "模板2: 1510×37, 1720×10, 1900×49"]
    )
    
    templates = {
        "模板1: 1810×51, 1715×86, 1860×26": "1810,51\n1715,86\n1860,26",
        "模板2: 1510×37, 1720×10, 1900×49": "1510,37\n1720,10\n1900,49"
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
    order_df = pd.DataFrame([(w, q) for w, q in orders.items()], columns=['宽度(mm)', '数量'])
    st.dataframe(order_df, use_container_width=True)
    
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
            
            # 按方案类型分组显示
            for i, plan in enumerate(result['production_plan']):
                col1, col2, col3 = st.columns([3, 1, 2])
                with col1:
                    st.write(f"**{plan['pattern']}**")
                with col2:
                    st.write(f"×{plan['runs']}车")
                with col3:
                    st.write(f"利用率: {plan['utilization']*100:.1f}%")
            
            # 详细数据表
            with st.expander("查看详细数据"):
                display_df = plan_df[['pattern', 'runs', '利用率%', 'pattern_type']]
                st.dataframe(display_df, use_container_width=True)
        else:
            st.warning("未生成生产计划")
        
        # 生产完成情况
        st.subheader("✅ 生产完成情况")
        
        completion_data = []
        for width in orders.keys():
            ordered = orders[width]
            actual = result['actual_production'][width]
            diff = actual - ordered
            completion_data.append((width, ordered, actual, diff))
        
        completion_df = pd.DataFrame(completion_data, 
                                   columns=['规格', '订单数量', '实际生产', '差异'])
        st.dataframe(completion_df, use_container_width=True)
        
        # 分析超额生产情况
        overproduction = [diff for diff in completion_df['差异'] if diff > 0]
        if overproduction:
            st.info(f"📦 允许超额生产: 最大{max(overproduction)}件，总计{sum(overproduction)}件")
        
        # 生产效率分析
        st.subheader("📊 生产效率分析")
        
        if result['production_plan']:
            avg_runs_per_pattern = result['total_coils'] / len(result['production_plan'])
            total_pattern_changes = result['pattern_types'] - 1
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("平均单方案运行车数", f"{avg_runs_per_pattern:.1f}")
            with col2:
                st.metric("预计换刀次数", total_pattern_changes)
        
        # 优化建议
        st.subheader("💡 生产建议")
        
        if result['utilization_rate'] > 0.92 and result['pattern_types'] <= 2:
            st.success("🎉 **优秀方案**：高利用率 + 少换刀次数，建议按此方案组织生产")
        elif result['utilization_rate'] > 0.88:
            st.info("👍 **良好方案**：平衡了利用率和生产效率，适合批量生产")
        else:
            st.warning("⚠️ **待优化方案**：建议调整参数重新计算")
        
        # 下载生产计划
        if result['production_plan']:
            csv = pd.DataFrame(result['production_plan'])[['pattern', 'runs', 'utilization']].to_csv(index=False)
            st.download_button(
                label="📥 下载生产计划",
                data=csv,
                file_name=f"恒丰纸业生产计划_{time.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
