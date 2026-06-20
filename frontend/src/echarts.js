// vue-echarts는 필요한 차트/컴포넌트만 골라 등록(use)하는 방식 → 번들 용량 절약.
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  DataZoomComponent,
  AxisPointerComponent,
  VisualMapComponent,
  BrushComponent,
  ToolboxComponent,
} from 'echarts/components'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  ScatterChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  DataZoomComponent,
  AxisPointerComponent,
  VisualMapComponent,
  BrushComponent,
  ToolboxComponent,
])
