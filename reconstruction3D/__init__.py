"""
3D реконструкция печени из сегментированных масок
"""
import numpy as np
import pyvista as pv
from typing import Dict, Any, Tuple
import tempfile
import os


class Reconstruction3D:
    """Класс для 3D реконструкции печени"""

    def __init__(self):
        pass

    def reconstruct_from_masks(self,
                               masks_3d: np.ndarray,
                               spacing: Tuple[float, float, float] = (1.0, 1.0, 3.0)) -> Dict[str, Any]:
        """
        Реконструкция 3D модели из 3D масок
        """
        try:
            print(f"🔨 Начинаю 3D реконструкцию: {masks_3d.shape}")

            # Создаем 3D объем из масок
            volume = masks_3d.astype(np.uint8)

            # Создаем сетку PyVista
            grid = pv.UniformGrid()
            grid.dimensions = np.array(volume.shape) + 1
            grid.spacing = spacing  # (x, y, z) spacing в мм
            grid.origin = (0, 0, 0)

            # Добавляем данные объема
            grid.cell_data["values"] = volume.flatten(order="F")

            # Извлекаем изоповерхность (Marching Cubes)
            mesh = grid.contour([0.5])

            # Постобработка меша
            mesh = self._postprocess_mesh(mesh)

            # Расчет метрик
            metrics = self._calculate_metrics(mesh, spacing)

            # Экспорт во временные файлы
            export_paths = self._export_mesh(mesh)

            return {
                "success": True,
                "mesh": mesh,
                "metrics": metrics,
                "export_paths": export_paths,
                "num_vertices": mesh.n_points,
                "num_faces": mesh.n_cells
            }

        except Exception as e:
            print(f"❌ Ошибка 3D реконструкции: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _postprocess_mesh(self, mesh: pv.PolyData) -> pv.PolyData:
        """Постобработка 3D меша"""
        # 1. Удаление мелких несвязных компонентов
        if mesh.n_cells > 1:
            mesh = mesh.extract_largest()

        # 2. Заполнение отверстий
        mesh = mesh.fill_holes(1000)

        # 3. Сглаживание
        mesh = mesh.smooth(n_iter=50, relaxation_factor=0.1)

        # 4. Редукция полигонов (опционально, если много полигонов)
        if mesh.n_cells > 50000:
            mesh = mesh.decimate(0.5)

        return mesh

    def _calculate_metrics(self, mesh: pv.PolyData, spacing: Tuple) -> Dict[str, float]:
        """Расчет метрик объема и площади"""
        # Объем в мм³
        volume_mm3 = mesh.volume

        # Учитываем spacing для реальных размеров
        voxel_volume = spacing[0] * spacing[1] * spacing[2]
        real_volume_mm3 = volume_mm3 * voxel_volume

        # Конвертация в мл (1 мл = 1000 мм³)
        volume_ml = real_volume_mm3 / 1000.0

        # Площадь поверхности
        surface_area_mm2 = mesh.area * spacing[0] * spacing[1]
        surface_area_cm2 = surface_area_mm2 / 100.0

        return {
            "volume_ml": float(volume_ml),
            "volume_mm3": float(real_volume_mm3),
            "surface_area_cm2": float(surface_area_cm2),
            "surface_area_mm2": float(surface_area_mm2),
            "spacing_x": spacing[0],
            "spacing_y": spacing[1],
            "spacing_z": spacing[2]
        }

    def _export_mesh(self, mesh: pv.PolyData) -> Dict[str, str]:
        """Экспорт меша в разные форматы"""
        export_paths = {}

        # Создаем временные файлы
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_stl:
            mesh.save(tmp_stl.name)
            export_paths['stl'] = tmp_stl.name

        with tempfile.NamedTemporaryFile(suffix='.ply', delete=False) as tmp_ply:
            mesh.save(tmp_ply.name)
            export_paths['ply'] = tmp_ply.name

        return export_paths