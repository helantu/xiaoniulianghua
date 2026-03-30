"""
量化规则引擎 - 可扩展的规则系统，支持自定义策略
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from .analyzer import SignalScore

logger = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    """交易决策"""
    should_trade: bool = False
    action: str = "HOLD"       # BUY / SELL / HOLD
    trade_type: str = "SPOT"   # SPOT / FUTURES
    quantity_pct: float = 0.1  # 仓位百分比
    leverage: int = 1          # 合约杠杆
    reason: str = ""
    score: float = 0.0


class BaseRule(ABC):
    """规则基类 - 所有自定义规则必须继承此类"""

    name: str = "未命名规则"
    description: str = ""
    enabled: bool = True

    @abstractmethod
    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        """
        评估规则，返回交易决策或None(不操作)
        context包含: balance, positions, params等上下文信息
        """
        pass


# ==================== 内置规则 ====================

class ScoreBasedBuyRule(BaseRule):
    """基于评分的买入规则（核心默认规则）"""
    name = "评分买入规则"
    description = "当9分制评分达到阈值时触发买入"

    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        params = context.get('params', {})
        threshold = params.get('buy_threshold', 6.0)
        qty_pct = params.get('buy_quantity_pct', 0.1)

        if score.total_score >= threshold and score.signal == "BUY":
            return TradeDecision(
                should_trade=True,
                action="BUY",
                trade_type="SPOT",
                quantity_pct=qty_pct,
                reason=f"评分{score.total_score:.1f}≥阈值{threshold}，买入信号",
                score=score.total_score
            )
        return None


class ScoreBasedSellRule(BaseRule):
    """基于评分的卖出规则"""
    name = "评分卖出规则"
    description = "当9分制评分低于卖出阈值时触发卖出"

    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        params = context.get('params', {})
        sell_threshold = params.get('sell_threshold', 2.0)

        if score.total_score <= sell_threshold and score.signal == "SELL":
            return TradeDecision(
                should_trade=True,
                action="SELL",
                trade_type="SPOT",
                quantity_pct=1.0,  # 全仓卖出
                reason=f"评分{score.total_score:.1f}≤阈值{sell_threshold}，卖出信号",
                score=score.total_score
            )
        return None


class StopLossRule(BaseRule):
    """止损规则"""
    name = "止损规则"
    description = "持仓亏损超过设定比例时强制止损"

    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        params = context.get('params', {})
        stop_loss_pct = params.get('stop_loss_pct', 5.0)  # 默认5%止损
        positions = context.get('positions', {})

        symbol = score.symbol
        if symbol in positions:
            pos = positions[symbol]
            entry_price = pos.get('entry_price', 0)
            if entry_price > 0:
                loss_pct = (score.price - entry_price) / entry_price * 100
                if loss_pct <= -stop_loss_pct:
                    return TradeDecision(
                        should_trade=True,
                        action="SELL",
                        trade_type="SPOT",
                        quantity_pct=1.0,
                        reason=f"触发止损! 亏损{loss_pct:.2f}%",
                        score=score.total_score
                    )
        return None


class TakeProfitRule(BaseRule):
    """止盈规则"""
    name = "止盈规则"
    description = "持仓盈利超过设定比例时获利了结"

    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        params = context.get('params', {})
        take_profit_pct = params.get('take_profit_pct', 10.0)  # 默认10%止盈
        positions = context.get('positions', {})

        symbol = score.symbol
        if symbol in positions:
            pos = positions[symbol]
            entry_price = pos.get('entry_price', 0)
            if entry_price > 0:
                profit_pct = (score.price - entry_price) / entry_price * 100
                if profit_pct >= take_profit_pct:
                    return TradeDecision(
                        should_trade=True,
                        action="SELL",
                        trade_type="SPOT",
                        quantity_pct=1.0,
                        reason=f"触发止盈! 盈利{profit_pct:.2f}%",
                        score=score.total_score
                    )
        return None


class FuturesLongRule(BaseRule):
    """合约做多规则"""
    name = "合约做多规则"
    description = "评分高时开合约多单"
    enabled = False  # 默认关闭，需手动开启

    def evaluate(self, score: SignalScore, context: dict) -> Optional[TradeDecision]:
        params = context.get('params', {})
        if not params.get('futures_enabled', False):
            return None

        threshold = params.get('futures_buy_threshold', 7.0)
        leverage = params.get('futures_leverage', 3)

        if score.total_score >= threshold:
            return TradeDecision(
                should_trade=True,
                action="BUY",
                trade_type="FUTURES",
                quantity_pct=params.get('futures_qty_pct', 0.05),
                leverage=leverage,
                reason=f"合约做多 评分{score.total_score:.1f}≥{threshold}",
                score=score.total_score
            )
        return None


# ==================== 规则引擎 ====================

class RuleEngine:
    """规则引擎 - 管理和执行所有规则"""

    def __init__(self):
        self._rules: list[BaseRule] = []
        self._load_default_rules()

    def _load_default_rules(self):
        """加载默认规则"""
        self._rules = [
            ScoreBasedBuyRule(),
            ScoreBasedSellRule(),
            StopLossRule(),
            TakeProfitRule(),
            FuturesLongRule(),
        ]
        logger.info(f"已加载 {len(self._rules)} 条规则")

    def add_rule(self, rule: BaseRule):
        """添加自定义规则"""
        self._rules.append(rule)
        logger.info(f"已添加规则: {rule.name}")

    def remove_rule(self, rule_name: str):
        """删除规则"""
        self._rules = [r for r in self._rules if r.name != rule_name]

    def toggle_rule(self, rule_name: str, enabled: bool):
        """启用/禁用规则"""
        for rule in self._rules:
            if rule.name == rule_name:
                rule.enabled = enabled
                logger.info(f"规则 '{rule_name}' {'已启用' if enabled else '已禁用'}")
                return

    def get_rules_info(self) -> list:
        """获取所有规则信息"""
        return [
            {
                'name': r.name,
                'description': r.description,
                'enabled': r.enabled,
                'type': r.__class__.__name__
            }
            for r in self._rules
        ]

    def evaluate(self, score: SignalScore, context: dict) -> list[TradeDecision]:
        """
        执行所有规则，返回所有触发的决策列表
        优先级：止损 > 止盈 > 信号买卖
        """
        decisions = []

        # 先执行风控规则（止损/止盈优先级最高）
        priority_rules = ['止损规则', '止盈规则']
        other_rules = [r for r in self._rules if r.name not in priority_rules]
        sorted_rules = [r for r in self._rules if r.name in priority_rules] + other_rules

        for rule in sorted_rules:
            if not rule.enabled:
                continue
            try:
                decision = rule.evaluate(score, context)
                if decision and decision.should_trade:
                    decisions.append(decision)
                    logger.info(f"规则触发[{rule.name}]: {decision.action} {score.symbol} - {decision.reason}")
                    # 止损/止盈触发后不再执行其他规则
                    if rule.name in priority_rules:
                        break
            except Exception as e:
                logger.error(f"规则 '{rule.name}' 执行失败: {e}")

        return decisions
