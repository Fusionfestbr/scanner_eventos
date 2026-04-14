"""
Checkpoints para recuperação do pipeline.
Salva o estado em pontos críticos do pipeline para recuperação automática.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from utils.logger import logger

CHECKPOINT_DIR = Path(__file__).parent.parent / "data"
CHECKPOINT_FILE = CHECKPOINT_DIR / "pipeline_state.json"


class PipelineCheckpoint:
    """
    Gerenciador de checkpoints para o pipeline.
    
    Uso:
        checkpoint = PipelineCheckpoint()
        checkpoint.salvar(etapa="coleta", dados={"eventos": [...], "qtd": 100})
        
        # Ao reiniciar:
        estado = checkpoint.carregar()
        if estado and estado.get("etapa") == "coleta":
            # Recarregar dados da coleta
            ...
    """
    
    def __init__(self, filepath: str = None):
        self.filepath = Path(filepath) if filepath else CHECKPOINT_FILE
        self._garantir_diretorio()
    
    def _garantir_diretorio(self):
        """Garante que o diretório existe."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def salvar(self, etapa: str, dados: dict, forcar: bool = False) -> bool:
        """
        Salva checkpoint do pipeline.
        
        Args:
            etapa: Nome da etapa (coleta, validacao, analise, decisao)
            dados: Dados a salvar (eventos, métricas, etc.)
            forcar: Se True, sobrescreve checkpoint existente
            
        Returns:
            True se salvou com sucesso
        """
        try:
            existente = self.carregar()
            
            if existente and not forcar:
                if existente.get("etapa") == etapa:
                    logger.info(f"Checkpoint ja existe para {etapa}, pulando")
                    return True
            
            estado = {
                "etapa": etapa,
                "timestamp": datetime.now().isoformat(),
                "dados": dados,
                "pipeline_id": os.environ.get("PIPELINE_ID", str(int(time.time())))
            }
            
            temp_file = self.filepath.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)
            
            temp_file.replace(self.filepath)
            
            logger.info(f"Checkpoint salvo: {etapa}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar checkpoint: {e}")
            return False
    
    def carregar(self, etapes_validas: list = None) -> Optional[dict]:
        """
        Carrega checkpoint existente.
        
        Args:
            etapes_validas: Lista de etapas válidas. Se None, carrega qualquer checkpoint.
            
        Returns:
            Dict com checkpoint ou None
        """
        if not self.filepath.exists():
            return None
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                estado = json.load(f)
            
            etapa = estado.get("etapa")
            
            if etapes_validas and etapa not in etapes_validas:
                logger.info(f"Checkpoint de {etapa} não é válido para {etapes_validas}")
                return None
            
            logger.info(f"Checkpoint carregado: {etapa} de {estado.get('timestamp')}")
            return estado
            
        except Exception as e:
            logger.error(f"Erro ao carregar checkpoint: {e}")
            return None
    
    def limpar(self) -> bool:
        """Remove checkpoint."""
        try:
            if self.filepath.exists():
                self.filepath.unlink()
                logger.info("Checkpoint removido")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar checkpoint: {e}")
            return False
    
    def existe(self) -> bool:
        """Verifica se existe checkpoint."""
        return self.filepath.exists()
    
    def get_etapa(self) -> Optional[str]:
        """Retorna a etapa do checkpoint atual."""
        estado = self.carregar()
        return estado.get("etapa") if estado else None
    
    def get_timestamp(self) -> Optional[str]:
        """Retorna timestamp do checkpoint."""
        estado = self.carregar()
        return estado.get("timestamp") if estado else None


class EstadoPipeline:
    """
    Estado em memória do pipeline para trackamento contínuo.
    Útil para modo --daemon.
    """
    
    def __init__(self):
        self._estado = {
            "inicio": None,
            "etapa_atual": None,
            "progresso": 0,
            "eventos": {},
            "metricas": {},
            "erros": []
        }
    
    def iniciar(self, pipeline_id: str = None):
        """Marca início de novo pipeline."""
        self._estado = {
            "inicio": datetime.now().isoformat(),
            "etapa_atual": "iniciando",
            "progresso": 0,
            "eventos": {},
            "metricas": {},
            "erros": [],
            "pipeline_id": pipeline_id or str(int(time.time()))
        }
        logger.info(f"Pipeline iniciado: {self._estado['pipeline_id']}")
    
    def etapa(self, nome: str, progresso: int):
        """Atualiza etapa atual."""
        self._estado["etapa_atual"] = nome
        self._estado["progresso"] = progresso
        logger.debug(f"Etapa: {nome} ({progresso}%)")
    
    def adicionar_evento(self, key: str, dados: Any):
        """Adiciona dados de evento."""
        self._estado["eventos"][key] = dados
    
    def adicionar_metrica(self, key: str, valor: Any):
        """Adiciona métrica."""
        self._estado["metricas"][key] = valor
    
    def adicionar_erro(self, erro: str):
        """Registra erro."""
        self._estado["erros"].append({
            "timestamp": datetime.now().isoformat(),
            "erro": erro
        })
        logger.error(f"Erro registrado: {erro}")
    
    def get_estado(self) -> dict:
        """Retorna estado atual."""
        return self._estado.copy()
    
    def get_etapa_atual(self) -> str:
        """Retorna etapa atual."""
        return self._estado.get("etapa_atual", "desconhecido")
    
    def get_progresso(self) -> int:
        """Retorna progresso."""
        return self._estado.get("progresso", 0)
    
    def esta_em_andamento(self) -> bool:
        """Verifica se pipeline está em andamento."""
        return self._estado.get("etapa_atual") not in [None, "concluido", "desconhecido"]
    
    def get_erros(self) -> list:
        """Retorna lista de erros."""
        return self._estado.get("erros", [])
    
    def esta_saudavel(self, max_erros: int = 5) -> bool:
        """Verifica se pipeline está saudável."""
        return len(self._estado.get("erros", [])) < max_erros


_checkpoint: Optional[PipelineCheckpoint] = None
_estado_pipeline: Optional[EstadoPipeline] = None


def get_checkpoint() -> PipelineCheckpoint:
    """Retorna gerenciador de checkpoints (singleton)."""
    global _checkpoint
    if _checkpoint is None:
        _checkpoint = PipelineCheckpoint()
    return _checkpoint


def get_estado_pipeline() -> EstadoPipeline:
    """Retorna estado do pipeline em memória (singleton)."""
    global _estado_pipeline
    if _estado_pipeline is None:
        _estado_pipeline = EstadoPipeline()
    return _estado_pipeline