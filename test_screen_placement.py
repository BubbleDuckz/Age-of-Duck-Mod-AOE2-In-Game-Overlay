import unittest
from PyQt5.QtCore import QRect,QPoint
from screen_placement import visible_position
class PlacementTests(unittest.TestCase):
 def test_actual_offscreen_position(self):
  self.assertEqual(visible_position(QRect(2593,104,407,148),[QRect(0,0,2560,1440)]),QPoint(2153,104))
 def test_existing_valid_position_unchanged(self):
  self.assertEqual(visible_position(QRect(40,80,407,148),[QRect(0,0,1920,1080)]),QPoint(40,80))
 def test_negative_monitor_valid(self):
  self.assertEqual(visible_position(QRect(-1500,80,407,148),[QRect(0,0,1920,1080),QRect(-1920,0,1920,1080)]),QPoint(-1500,80))
 def test_removed_monitor_and_large_panel(self):
  self.assertEqual(visible_position(QRect(-1500,80,2500,1200),[QRect(0,0,1920,1080)]),QPoint(0,0))
