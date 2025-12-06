import React, { useRef, useEffect, useState, useCallback } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

interface ThreeDViewerProps {
  stlBase64?: string;
  stlUrl?: string;
  onLoad?: (mesh: THREE.Mesh) => void;
  onError?: (error: Error) => void;
}

const ThreeDViewer: React.FC<ThreeDViewerProps> = ({
  stlBase64,
  stlUrl,
  onLoad,
  onError
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshRef = useRef<THREE.Mesh | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [meshInfo, setMeshInfo] = useState<{vertices: number, faces: number} | null>(null);

  // Инициализация сцены
  const initScene = useCallback(() => {
    if (!mountRef.current) return;

    // Очищаем предыдущую сцену
    if (rendererRef.current && mountRef.current.contains(rendererRef.current.domElement)) {
      mountRef.current.removeChild(rendererRef.current.domElement);
    }

    // Создаем сцену
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);

    // Создаем камеру
    const camera = new THREE.PerspectiveCamera(
      75,
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.z = 100;

    // Создаем рендерер
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Добавляем освещение
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 5);
    scene.add(directionalLight);

    // Добавляем сетку
    const gridHelper = new THREE.GridHelper(200, 40, 0x888888, 0x444444);
    scene.add(gridHelper);

    // Добавляем оси
    const axesHelper = new THREE.AxesHelper(50);
    scene.add(axesHelper);

    // Добавляем контролы
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Добавляем на страницу
    mountRef.current.appendChild(renderer.domElement);

    // Сохраняем ссылки
    sceneRef.current = scene;
    cameraRef.current = camera;
    rendererRef.current = renderer;
    controlsRef.current = controls;

    // Функция анимации
    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      if (renderer && mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Обработка изменения размера
  const handleResize = useCallback(() => {
    if (!mountRef.current || !cameraRef.current || !rendererRef.current) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    cameraRef.current.aspect = width / height;
    cameraRef.current.updateProjectionMatrix();
    rendererRef.current.setSize(width, height);
  }, []);

  // Загрузка STL модели
  const loadSTLModel = useCallback(async (base64?: string, url?: string) => {
    if (!sceneRef.current || !cameraRef.current || !controlsRef.current) return;

    setLoading(true);
    setError(null);

    try {
      // Удаляем предыдущую модель
      if (meshRef.current && sceneRef.current) {
        sceneRef.current.remove(meshRef.current);
        meshRef.current.geometry.dispose();
        if (meshRef.current.material instanceof THREE.Material) {
          meshRef.current.material.dispose();
        }
        meshRef.current = null;
      }

      let buffer: ArrayBuffer;

      if (base64) {
        // Декодируем base64
        const binaryString = atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        buffer = bytes.buffer;
      } else if (url) {
        // Загружаем по URL
        const response = await fetch(url);
        buffer = await response.arrayBuffer();
      } else {
        throw new Error('Не предоставлены данные STL');
      }

      // Загружаем STL
      const loader = new STLLoader();
      const geometry = loader.parse(buffer);

      // Центрируем геометрию
      geometry.center();

      // Создаем материал для печени
      const material = new THREE.MeshPhongMaterial({
        color: 0x00a86b,
        specular: 0x111111,
        shininess: 200,
        transparent: true,
        opacity: 0.85
      });

      const mesh = new THREE.Mesh(geometry, material);
      meshRef.current = mesh;

      // Добавляем каркас
      const wireframe = new THREE.WireframeGeometry(geometry);
      const wireframeMesh = new THREE.LineSegments(wireframe);
      wireframeMesh.material = new THREE.LineBasicMaterial({
        color: 0x000000,
        linewidth: 1,
        transparent: true,
        opacity: 0.3
      });
      mesh.add(wireframeMesh);

      sceneRef.current.add(mesh);

      // Настраиваем камеру под модель
      const box = new THREE.Box3().setFromObject(mesh);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());

      const maxDim = Math.max(size.x, size.y, size.z);
      const fov = cameraRef.current.fov * (Math.PI / 180);
      let cameraZ = Math.abs(maxDim / Math.tan(fov / 2));
      cameraZ *= 1.5;

      cameraRef.current.position.z = cameraZ;
      controlsRef.current.target.copy(center);
      controlsRef.current.update();

      setMeshInfo({
        vertices: geometry.attributes.position.count,
        faces: geometry.index ? geometry.index.count / 3 : 0
      });

      setLoading(false);

      if (onLoad) {
        onLoad(mesh);
      }

    } catch (err) {
      console.error('Ошибка загрузки STL:', err);
      setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
      setLoading(false);

      if (onError) {
        onError(err instanceof Error ? err : new Error('Неизвестная ошибка'));
      }
    }
  }, [onLoad, onError]);

  // Инициализация при монтировании
  useEffect(() => {
    const cleanup = initScene();

    // Обработка ресайза
    window.addEventListener('resize', handleResize);

    // Загружаем модель если есть данные
    if (stlBase64 || stlUrl) {
      loadSTLModel(stlBase64, stlUrl);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      if (cleanup) cleanup();
    };
  }, [initScene, handleResize]);

  // Обновляем модель при изменении данных
  useEffect(() => {
    if (stlBase64 || stlUrl) {
      loadSTLModel(stlBase64, stlUrl);
    }
  }, [stlBase64, stlUrl, loadSTLModel]);

  return (
    <div className="three-d-viewer" style={{ position: 'relative', width: '100%', height: '500px' }}>
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {loading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'rgba(255, 255, 255, 0.9)',
          padding: '20px',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
          zIndex: 1000
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ marginBottom: '10px' }}>⏳ Загрузка 3D модели...</div>
            <div style={{ fontSize: '12px', color: '#666' }}>Может занять несколько секунд</div>
          </div>
        </div>
      )}

      {error && (
        <div style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          background: 'rgba(220, 53, 69, 0.9)',
          color: 'white',
          padding: '10px 15px',
          borderRadius: '5px',
          zIndex: 1000,
          maxWidth: '80%'
        }}>
          <strong>Ошибка:</strong> {error}
        </div>
      )}

      {meshInfo && !loading && (
        <div style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'rgba(255, 255, 255, 0.8)',
          padding: '8px 12px',
          borderRadius: '5px',
          fontSize: '12px',
          zIndex: 1000
        }}>
          <div>Вершин: {meshInfo.vertices.toLocaleString()}</div>
          <div>Граней: {meshInfo.faces.toLocaleString()}</div>
        </div>
      )}

      <div style={{
        position: 'absolute',
        bottom: '10px',
        left: '10px',
        background: 'rgba(255, 255, 255, 0.8)',
        padding: '6px 10px',
        borderRadius: '5px',
        fontSize: '11px',
        zIndex: 1000
      }}>
        Управление: ЛКМ - вращение, ПКМ - панорамирование, Колесо - масштаб
      </div>
    </div>
  );
};

export default ThreeDViewer;