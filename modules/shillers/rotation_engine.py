import random
from typing import List, Dict, Set, Tuple
from loguru import logger


class RotationEngine:
    """
    Движок для управления ротацией шиллеров в кольцах

    Основной принцип из ТЗ:
    - Никогда не взаимодействовать с тем же участником два раунда подряд
    - Максимум одно повторение за 3+ раунда
    """

    def __init__(self, ring_size: int):
        """
        Args:
            ring_size: Размер кольца (количество участников)
        """
        self.ring_size = ring_size
        self.history = []  # История всех ротаций
        self.interaction_count = {}  # Счетчик взаимодействий между парами

    def generate_rotation(self, round_number: int) -> List[Dict[str, int]]:
        """
        Генерировать схему ротации для раунда

        Args:
            round_number: Номер раунда

        Returns:
            Список взаимодействий в формате [{"from": 0, "to": 1}, ...]
        """
        if round_number == 1:
            # Первый раунд - простое кольцо
            return self._generate_simple_ring()

        # Для последующих раундов используем сложную логику
        return self._generate_complex_rotation(round_number)

    def _generate_simple_ring(self) -> List[Dict[str, int]]:
        """Генерировать простое кольцо для первого раунда"""
        rotation = []
        for i in range(self.ring_size):
            next_idx = (i + 1) % self.ring_size
            rotation.append({
                "from": i,
                "to": next_idx,
                "round": 1
            })

            # Обновляем счетчик взаимодействий
            self._update_interaction_count(i, next_idx)

        self.history.append(rotation)
        return rotation

    def _generate_complex_rotation(self, round_number: int) -> List[Dict[str, int]]:
        """Генерировать сложную ротацию с учетом истории"""
        rotation = []
        used_sources = set()
        used_targets = set()

        # Получаем запрещенные пары из предыдущего раунда
        forbidden_pairs = self._get_forbidden_pairs()

        # Создаем все возможные пары
        all_pairs = []
        for i in range(self.ring_size):
            for j in range(self.ring_size):
                if i != j:  # Не с самим собой
                    all_pairs.append((i, j))

        # Сортируем пары по приоритету (меньше взаимодействий = выше приоритет)
        all_pairs.sort(key=lambda p: self.interaction_count.get(p, 0))

        # Пытаемся создать валидную ротацию
        attempts = 0
        max_attempts = 100

        while len(rotation) < self.ring_size and attempts < max_attempts:
            attempts += 1

            # Ищем валидную пару
            for source, target in all_pairs:
                if (source not in used_sources and
                        target not in used_targets and
                        (source, target) not in forbidden_pairs):
                    rotation.append({
                        "from": source,
                        "to": target,
                        "round": round_number
                    })

                    used_sources.add(source)
                    used_targets.add(target)
                    self._update_interaction_count(source, target)
                    break

            # Если не можем найти валидную пару, сбрасываем и пробуем снова
            if len(used_sources) < self.ring_size and len(rotation) == len(used_sources):
                # Застряли, пробуем другой подход
                rotation = []
                used_sources.clear()
                used_targets.clear()
                random.shuffle(all_pairs)

        # Если не удалось создать полную ротацию, используем fallback
        if len(rotation) < self.ring_size:
            logger.warning(f"Не удалось создать полную ротацию, используем fallback")
            rotation = self._generate_fallback_rotation(round_number, used_sources)

        self.history.append(rotation)
        return rotation

    def _get_forbidden_pairs(self) -> Set[Tuple[int, int]]:
        """Получить запрещенные пары из предыдущего раунда"""
        if not self.history:
            return set()

        forbidden = set()
        last_rotation = self.history[-1]

        for interaction in last_rotation:
            forbidden.add((interaction["from"], interaction["to"]))

        return forbidden

    def _update_interaction_count(self, source: int, target: int):
        """Обновить счетчик взаимодействий"""
        pair = (source, target)
        self.interaction_count[pair] = self.interaction_count.get(pair, 0) + 1

    def _generate_fallback_rotation(self, round_number: int,
                                    exclude_sources: Set[int]) -> List[Dict[str, int]]:
        """Генерировать запасную ротацию когда основной алгоритм не работает"""
        rotation = []
        participants = list(range(self.ring_size))

        # Перемешиваем участников
        random.shuffle(participants)

        # Создаем пары последовательно
        for i in range(0, len(participants) - 1, 2):
            if i + 1 < len(participants):
                rotation.append({
                    "from": participants[i],
                    "to": participants[i + 1],
                    "round": round_number
                })
                rotation.append({
                    "from": participants[i + 1],
                    "to": participants[i],
                    "round": round_number
                })

        return rotation

    def get_rotation_matrix(self) -> Dict[str, List[List[int]]]:
        """
        Получить матрицу ротаций для визуализации

        Returns:
            Словарь с матрицами для каждого раунда
        """
        matrices = {}

        for round_idx, rotation in enumerate(self.history):
            matrix = [[0] * self.ring_size for _ in range(self.ring_size)]

            for interaction in rotation:
                matrix[interaction["from"]][interaction["to"]] = 1

            matrices[f"round_{round_idx + 1}"] = matrix

        return matrices

    def validate_rotation(self, rotation: List[Dict[str, int]]) -> bool:
        """
        Проверить валидность ротации

        Правила:
        1. Каждый участник должен взаимодействовать ровно один раз как источник
        2. Никто не взаимодействует сам с собой
        3. Нет повторений с предыдущим раундом
        """
        sources = set()
        targets = set()

        # Проверяем базовые правила
        for interaction in rotation:
            source = interaction["from"]
            target = interaction["to"]

            # Не с самим собой
            if source == target:
                return False

            # Каждый источник только один раз
            if source in sources:
                return False

            sources.add(source)
            targets.add(target)

        # Все должны участвовать
        if len(sources) != self.ring_size:
            return False

        # Проверяем повторения с предыдущим раундом
        if self.history:
            forbidden_pairs = self._get_forbidden_pairs()
            for interaction in rotation:
                if (interaction["from"], interaction["to"]) in forbidden_pairs:
                    return False

        return True

    def get_statistics(self) -> Dict:
        """Получить статистику ротаций"""
        total_interactions = sum(self.interaction_count.values())
        unique_pairs = len(self.interaction_count)
        max_interactions = max(self.interaction_count.values()) if self.interaction_count else 0

        # Находим наиболее частые пары
        frequent_pairs = sorted(
            self.interaction_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_rounds": len(self.history),
            "total_interactions": total_interactions,
            "unique_pairs": unique_pairs,
            "max_interactions_per_pair": max_interactions,
            "average_interactions_per_pair": total_interactions / unique_pairs if unique_pairs > 0 else 0,
            "most_frequent_pairs": frequent_pairs,
        }