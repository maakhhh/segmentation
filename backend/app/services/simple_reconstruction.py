"""
Упрощенная версия 3D реконструкции для тестирования ZIP архивов
"""
import numpy as np
import pyvista as pv
from typing import Dict, Any, Tuple
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


class SimpleReconstructionService:
    """Упрощенный сервис для 3D реконструкции"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="liver_simple_")
        logger.info(f"Инициализирован SimpleReconstructionService, temp dir: {self.temp_dir}")

    def create_demo_liver_model(self,
                                num_slices: int = 20,
                                spacing: Tuple[float, float, float] = (0.7, 0.7, 3.0)) -> Dict[str, Any]:
        """
        Создание демонстрационной модели печени (эллипсоид)
        """
        try:
            logger.info("Создаю демонстрационную модель печени...")

            # Создаем эллипсоид (форма, похожая на печень)
            # Используем параметрическое уравнение эллипсоида
            phi = np.linspace(0, 2 * np.pi, 50)
            theta = np.linspace(0, np.pi, 25)

            phi, theta = np.meshgrid(phi, theta)

            # Полуоси эллипсоида (похоже на печень)
            a = 60  # по x
            b = 45  # по y
            c = 80  # по z

            x = a * np.sin(theta) * np.cos(phi)
            y = b * np.sin(theta) * np.sin(phi)
            z = c * np.cos(theta)

            # Создаем сетку из точек
            points = np.column_stack((x.flatten(), y.flatten(), z.flatten()))

            # Создаем PolyData
            cloud = pv.PolyData(points)

            # Восстанавливаем поверхность
            mesh = cloud.delaunay_3d().extract_surface()

            # Сглаживаем
            mesh = mesh.smooth(n_iter=50, relaxation_factor=0.1)

            # Масштабируем согласно spacing
            mesh.points[:, 0] *= spacing[0]
            mesh.points[:, 1] *= spacing[1]
            mesh.points[:, 2] *= spacing[2]

            # Экспорт
            export_paths = self._export_mesh(mesh)

            # Метрики
            metrics = self._calculate_metrics(mesh, spacing)

            return {
                "success": True,
                "mesh_info": {
                    "num_vertices": mesh.n_points,
                    "num_faces": mesh.n_cells,
                    "bounds": mesh.bounds
                },
                "metrics": metrics,
                "export_paths": export_paths
            }

        except Exception as e:
            logger.error(f"Ошибка создания демо-модели: {str(e)}")
            return {"success": False, "error": str(e)}

    def reconstruct_from_volume_demo(self,
                                     volume_shape: Tuple[int, int, int],
                                     spacing: Tuple[float, float, float] = (0.7, 0.7, 3.0)) -> Dict[str, Any]:
        """
        Демонстрационная реконструкция по форме объема
        """
        try:
            logger.info(f"Демо-реконструкция для объема: {volume_shape}")

            # Создаем простую модель на основе размера объема
            # Размер модели пропорционален размеру объема
            scale_x = volume_shape[2] * spacing[0] / 100
            scale_y = volume_shape[1] * spacing[1] / 100
            scale_z = volume_shape[0] * spacing[2] / 100

            # Создаем эллипсоид
            ellipsoid = pv.ParametricEllipsoid(
                scale_x * 50,  # x-radius
                scale_y * 40,  # y-radius
                scale_z * 60  # z-radius
            )

            # Смещаем в центр
            bounds = ellipsoid.bounds
            center = [
                (bounds[1] + bounds[0]) / 2,
                (bounds[3] + bounds[2]) / 2,
                (bounds[5] + bounds[4]) / 2
            ]
            ellipsoid.translate([-c for c in center])

            # Сглаживаем
            mesh = ellipsoid.smooth(n_iter=30, relaxation_factor=0.1)

            # Экспорт
            export_paths = self._export_mesh(mesh)

            # Метрики
            metrics = self._calculate_metrics(mesh, spacing)

            return {
                "success": True,
                "mesh_info": {
                    "num_vertices": mesh.n_points,
                    "num_faces": mesh.n_cells,
                    "bounds": mesh.bounds
                },
                "metrics": metrics,
                "export_paths": export_paths
            }

        except Exception as e:
            logger.error(f"Ошибка демо-реконструкции: {str(e)}")
            return {"success": False, "error": str(e)}

    def _calculate_metrics(self, mesh: pv.PolyData, spacing: Tuple) -> Dict[str, float]:
        """Расчет метрик объема и площади"""
        try:
            # Проверяем, что меш не пустой
            if mesh.n_points == 0:
                return {
                    "volume_ml": 0.0,
                    "volume_mm3": 0.0,
                    "surface_area_cm2": 0.0,
                    "surface_area_mm2": 0.0,
                    "center_of_mass": [0.0, 0.0, 0.0],
                    "spacing_x": spacing[0],
                    "spacing_y": spacing[1],
                    "spacing_z": spacing[2],
                    "bounding_box": {
                        "x": [0.0, 0.0],
                        "y": [0.0, 0.0],
                        "z": [0.0, 0.0]
                    }
                }

            # Учитываем spacing для реальных размеров
            voxel_volume = spacing[0] * spacing[1] * spacing[2]
            volume_mm3 = mesh.volume * voxel_volume
            volume_ml = volume_mm3 / 1000.0

            # Площадь поверхности
            surface_area_mm2 = mesh.area * spacing[0] * spacing[1]
            surface_area_cm2 = surface_area_mm2 / 100.0

            # Центр масс
            center = mesh.center

            return {
                "volume_ml": float(volume_ml),
                "volume_mm3": float(volume_mm3),
                "surface_area_cm2": float(surface_area_cm2),
                "surface_area_mm2": float(surface_area_mm2),
                "center_of_mass": [float(center[0]), float(center[1]), float(center[2])],
                "spacing_x": spacing[0],
                "spacing_y": spacing[1],
                "spacing_z": spacing[2],
                "bounding_box": {
                    "x": [float(mesh.bounds[0]), float(mesh.bounds[1])],
                    "y": [float(mesh.bounds[2]), float(mesh.bounds[3])],
                    "z": [float(mesh.bounds[4]), float(mesh.bounds[5])]
                }
            }
        except Exception as e:
            logger.error(f"Ошибка расчета метрик: {str(e)}")
            return {}

    def _export_mesh(self, mesh: pv.PolyData) -> Dict[str, str]:
        """Экспорт меша в разные форматы"""
        try:
            export_paths = {}

            # STL формат
            stl_path = os.path.join(self.temp_dir, "model.stl")
            mesh.save(stl_path, binary=True)
            export_paths['stl'] = stl_path

            # PLY формат
            ply_path = os.path.join(self.temp_dir, "model.ply")
            mesh.save(ply_path, binary=True)
            export_paths['ply'] = ply_path

            logger.info(f"Экспортированы файлы: {list(export_paths.keys())}")
            return export_paths

        except Exception as e:
            logger.error(f"Ошибка экспорта меша: {str(e)}")
            return {}

    def cleanup_temp_files(self):
        """Очистка временных файлов"""
        import shutil
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Очищена временная директория: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Не удалось очистить временную директорию: {str(e)}")


# Создаем глобальный экземпляр
simple_reconstruction_service = SimpleReconstructionService()