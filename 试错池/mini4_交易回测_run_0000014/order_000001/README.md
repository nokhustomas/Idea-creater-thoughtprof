The previous response was treated as the README write. Let me proceed with writing all the necessary files now.

ACTION: write rules_example.json
<<<FILE
{
  "initial_capital": 1000000,
  "position_size_pct": 0.2,
  "max_positions": 3,
  "stop_loss_pct": 0.08,
  "take_profit_pct": 0.15,
  "max_hold_days": 20,
  "buy_conditions": [
    {"type": "ma_cross", "short": 5, "long": 20, "direction": "golden"},
    {"type": "breakout", "window": 20, "direction": "high"}
  ],
  "sell_conditions": [
    {"type": "ma_cross", "short": 5, "long": 20, "direction": "death"},
    {"type": "change_threshold", "threshold_pct": -0.05, "direction": "below"}
  ]
}
<<<FILE>>>