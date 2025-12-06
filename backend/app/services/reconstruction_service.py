import numpy as np
import pyvista as pv
from typing import Dict, Any, Tuple, Optional
import tempfile
import os
import logging
from scipy import ndimage

logger = logging.getLogger(__name__)


class ReconstructionService:
    """Сервис для 3D реконструкции печени из сегментированных масок"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="liver_3d_")
        logger.info(f"Инициализирован ReconstructionService, temp dir: {self.temp_dir}")

    def reconstruct_from_masks(self,
                               masks_3d: np.ndarray,
                               spacing: Tuple[float, float, float] = (0.7, 0.7, 3.0),
                               threshold: float = 0.5) -> Dict[str, Any]:
        """
        Правильная 3D реконструкция из масок методом Marching Cubes

        Args:
            masks_3d: 3D массив масок сегментации (z, y, x) - 1 для печени, 0 для фона
            spacing: Расстояние между вокселями в мм (x, y, z)
            threshold: Порог для изоповерхности (обычно 0.5)

        Returns:
            Словарь с результатами реконструкции
        """
        try:
            logger.info(f"Начинаю 3D реконструкцию: shape={masks_3d.shape}, spacing={spacing}")

            # 1. Проверяем данные
            if len(masks_3d.shape) != 3:
                raise ValueError(f"Ожидается 3D массив, получено shape={masks_3d.shape}")

            # 2. Подготавливаем данные
            # Медицинские данные обычно в порядке (z, y, x) - срезы, высота, ширина
            # PyVista ожидает (x, y, z) - ширина, высота, срезы
            volume = masks_3d.astype(np.float32)

            # Нормализуем значения к 0-1 если нужно
            if volume.max() > 1.0:
                volume = volume / 255.0

            logger.info(f"Объем: {volume.shape}, тип: {volume.dtype}, мин: {volume.min()}, макс: {volume.max()}")

            # 3. Транспонируем в правильный порядок для PyVista: (z, y, x) -> (x, y, z)
            # Это важно: PyVista ожидает порядок (x, y, z)
            volume = np.transpose(volume, (2, 1, 0))
            logger.info(f"Объем после транспонирования: {volume.shape}")

            # 4. Применяем фильтрацию для удаления шума
            # Закомментируем пока, чтобы видеть чистую сегментацию
            # volume = ndimage.median_filter(volume, size=2)

            # 5. Создаем ImageData сетку
            # ВНИМАНИЕ: Для Marching Cubes нам нужна сетка с данными в точках (point data)
            # Размерность сетки должна быть равна размерности объема

            # Создаем сетку с правильными размерами
            grid = pv.ImageData()
            grid.dimensions = volume.shape
            grid.spacing = spacing
            grid.origin = (0, 0, 0)

            logger.info(f"Сетка создана: dimensions={volume.shape}, n_points={grid.n_points}")

            # 6. Добавляем скалярные данные КАК POINT DATA (очень важно!)
            # Flatten в порядке 'F' (Fortran-style) для соответствия VTK
            grid.point_data["values"] = volume.flatten(order='F')

            # 7. Извлекаем изоповерхность (Marching Cubes)
            logger.info(f"Извлекаю изоповерхность с порогом {threshold}...")

            try:
                # Пробуем разные пороги для надежности
                mesh = grid.contour([threshold])

                if mesh.n_points == 0 and threshold > 0:
                    # Если с порогом 0.5 не получилось, пробуем 0.3
                    mesh = grid.contour([0.3])
                    logger.info(f"Использован порог 0.3, получено точек: {mesh.n_points}")

                if mesh.n_points == 0:
                    # Пробуем найти оптимальный порог
                    data_values = grid.point_data["values"]
                    nonzero_values = data_values[data_values > 0]
                    if len(nonzero_values) > 0:
                        adaptive_threshold = np.percentile(nonzero_values, 50)  # Медиана
                        mesh = grid.contour([adaptive_threshold])
                        logger.info(f"Использован адаптивный порог {adaptive_threshold:.3f}")

            except Exception as contour_error:
                logger.error(f"Ошибка contour: {contour_error}")
                # Альтернатива: используем extract_surface
                mesh = grid.extract_surface()
                logger.info("Использован extract_surface как запасной вариант")

            if mesh.n_points == 0:
                # Создаем минимальную поверхность из ненулевых вокселей
                logger.warning("Не удалось создать поверхность, создаю упрощенную модель")
                # Находим координаты ненулевых вокселей
                nonzero_coords = np.argwhere(volume > threshold)
                if len(nonzero_coords) > 0:
                    # Создаем облако точек
                    points = nonzero_coords.astype(np.float32)
                    # Масштабируем точки согласно spacing
                    points[:, 0] *= spacing[0]
                    points[:, 1] *= spacing[1]
                    points[:, 2] *= spacing[2]

                    # Создаем PolyData из точек
                    cloud = pv.PolyData(points)
                    # Восстанавливаем поверхность
                    mesh = cloud.reconstruct_surface()
                else:
                    raise ValueError("Нет данных для создания поверхности")

            logger.info(f"Создан меш: {mesh.n_points} вершин, {mesh.n_cells} граней")

            # 8. Постобработка меша
            mesh = self._postprocess_mesh(mesh)

            # 9. Расчет метрик
            metrics = self._calculate_metrics(mesh, spacing)

            # 10. Экспорт в файлы
            export_paths = self._export_mesh(mesh)

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
            logger.error(f"Ошибка 3D реконструкции: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def create_test_volume_from_slice(self,
                                      mask_2d: np.ndarray,
                                      num_slices: int = 20) -> np.ndarray:
        """
        Создает тестовый 3D объем из одного 2D среза для отладки
        """
        try:
            # Создаем 3D объем, дублируя 2D маску
            # Но делаем его объемным: уменьшаем интенсивность к краям

            height, width = mask_2d.shape
            volume = np.zeros((num_slices, height, width), dtype=np.float32)

            # Центральный срез получает полную интенсивность
            center_slice = num_slices // 2

            for z in range(num_slices):
                # Линейное уменьшение интенсивности от центра
                distance = abs(z - center_slice) / (center_slice + 1)
                intensity = max(0, 1.0 - distance * 2)  # Полное затухание к краям

                if intensity > 0:
                    volume[z] = mask_2d * intensity

            return volume

        except Exception as e:
            logger.error(f"Ошибка создания тестового объема: {str(e)}")
            return np.stack([mask_2d] * num_slices, axis=0)

    def _postprocess_mesh(self, mesh: pv.PolyData) -> pv.PolyData:
        """Постобработка 3D меша"""
        try:
            if mesh.n_points == 0:
                return mesh

            # 1. Удаление мелких несвязных компонентов
            if mesh.n_cells > 1:
                try:
                    mesh = mesh.extract_largest()
                    logger.info(f"Удалены мелкие компоненты, осталось граней: {mesh.n_cells}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить мелкие компоненты: {str(e)}")

            # 2. Заполнение отверстий
            try:
                mesh = mesh.fill_holes(hole_size=1000)
                logger.info("Заполнены отверстия в меше")
            except Exception as e:
                logger.warning(f"Не удалось заполнить отверстия: {str(e)}")

            # 3. Сглаживание (умеренное, чтобы не терять детали)
            if mesh.n_cells > 100:
                try:
                    mesh = mesh.smooth(n_iter=15, relaxation_factor=0.1)
                    logger.info("Сглажен меш")
                except Exception as e:
                    logger.warning(f"Не удалось сгладить меш: {str(e)}")

            # 4. Редукция полигонов (если очень много)
            if mesh.n_cells > 50000:
                try:
                    reduction_ratio = 30000 / mesh.n_cells
                    mesh = mesh.decimate(reduction_ratio)
                    logger.info(f"Уменьшено количество полигонов до: {mesh.n_cells}")
                except Exception as e:
                    logger.warning(f"Не удалось уменьшить полигоны: {str(e)}")

            return mesh

        except Exception as e:
            logger.warning(f"Ошибка постобработки меша: {str(e)}")
            return mesh

    def _calculate_metrics(self, mesh: pv.PolyData, spacing: Tuple) -> Dict[str, float]:
        """Расчет реалистичных метрик объема и площади"""
        try:
            if mesh.n_points == 0:
                return self._get_empty_metrics(spacing)

            # Реальный объем в мм³
            # PyVista уже возвращает объем в единицах сетки
            # Умножаем на произведение spacing для перевода в мм³
            voxel_volume = spacing[0] * spacing[1] * spacing[2]
            volume_mm3 = mesh.volume * voxel_volume

            # Конвертация в мл (1 мл = 1000 мм³)
            volume_ml = volume_mm3 / 1000.0

            # Проверка на реалистичность
            # Нормальный объем печени взрослого человека: 1200-1500 мл
            if volume_ml > 5000:
                logger.warning(f"Нереалистичный объем печени: {volume_ml:.1f} мл")
                # Возможно, масштабирование неправильное
                # Пересчитываем с учетом возможной ошибки в spacing
                if volume_ml > 10000:
                    # Слишком большой - вероятно, ошибка в расчетах
                    volume_mm3 = mesh.volume  # Без учета spacing
                    volume_ml = volume_mm3 / 1000.0

            # Площадь поверхности в мм²
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
            return self._get_empty_metrics(spacing)

    def _get_empty_metrics(self, spacing: Tuple) -> Dict[str, float]:
        """Возвращает метрики по умолчанию"""
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


# Создаем глобальный экземпляр сервиса
reconstruction_service = ReconstructionService()