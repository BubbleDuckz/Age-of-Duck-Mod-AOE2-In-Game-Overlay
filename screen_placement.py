"""Keep saved overlay positions on currently connected screens."""
from PyQt5.QtCore import QPoint,QRect

def visible_position(rect,areas):
    if not areas:return rect.topLeft()
    for area in areas:
        if area.contains(rect):return rect.topLeft()
    area=max(areas,key=lambda a:a.intersected(rect).width()*a.intersected(rect).height())
    x=max(area.left(),min(rect.left(),area.right()-rect.width()+1))
    y=max(area.top(),min(rect.top(),area.bottom()-rect.height()+1))
    return QPoint(x,y)
