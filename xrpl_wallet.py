from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
import logging
import asyncio
from xrpl.wallet import Wallet
from xrpl.clients import JsonRpcClient
from xrpl.models.transactions import Payment
from xrpl.models.requests import AccountInfo
from xrpl.utils import xrp_to_drops, drops_to_xrp
from xrpl.asyncio.transaction import submit_and_wait

@dataclass
class WalletConfig:
    """Configuração da carteira XRPL"""
    client: JsonRpcClient
    seed: Optional[str] = None

class XRPWallet:
    """Gerenciador simplificado de carteira XRPL"""
    
    def __init__(self, config: WalletConfig):
        self.client = config.client
        self.wallet = Wallet.from_seed(config.seed) if config.seed else Wallet.create()
        self.address = self.wallet.classic_address
        self._setup_logging()
        
    def _setup_logging(self):
        """Configura logging básico"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def get_balance(self) -> Decimal:
        """Retorna o saldo em XRP"""
        try:
            # Criar a requisição de informações da conta
            request = AccountInfo(
                account=self.address,
                ledger_index="validated"
            )
            
            # Fazer a requisição de forma síncrona
            response = self.client.request(request)
            
            # Processar o resultado
            if 'account_data' not in response.result:
                self.logger.warning("A conta ainda não foi ativada. É necessário depositar pelo menos 10 XRP para ativá-la.")
                print("\n🚨 A conta ainda não está ativada! Para ativá-la, envie pelo menos 10 XRP de teste pelo faucet:\n")
                print("🔗 Link: https://xrpl.org/xrp-testnet-faucet.html")
                print(f"📌 Endereço da carteira: {self.address}\n")
                return Decimal("0")
            
            balance = drops_to_xrp(response.result['account_data']['Balance'])
            self.logger.info(f"Saldo atual: {balance} XRP")
            return balance
        except Exception as e:
            self.logger.error(f"Erro ao buscar saldo: {e}")
            raise
            
    async def send_payment(self, destination: str, amount: Decimal) -> str:
        """Envia pagamento em XRP"""
        try:
            # Criar a transação de pagamento
            payment = Payment(
                account=self.address,
                amount=xrp_to_drops(amount),
                destination=destination
            )
            
            # Assinar e enviar a transação
            signed_tx = self.wallet.sign(payment)
            result = await submit_and_wait(signed_tx, self.client)
            
            # Verificar o resultado
            if result.result.get('meta', {}).get('TransactionResult') == 'tesSUCCESS':
                tx_hash = result.result['hash']
                self.logger.info(f"Pagamento realizado. Hash: {tx_hash}")
                return tx_hash
            else:
                raise Exception(f"Transação falhou: {result.result.get('meta', {}).get('TransactionResult')}")
                
        except Exception as e:
            self.logger.error(f"Erro ao enviar pagamento: {e}")
            raise

def create_testnet_wallet() -> XRPWallet:
    """Cria uma carteira de teste conectada à TestNet"""
    config = WalletConfig(
        client=JsonRpcClient("https://s.altnet.rippletest.net:51234")
    )
    return XRPWallet(config)

if __name__ == "__main__":
    # Criar a carteira
    wallet = create_testnet_wallet()
    print(f"\nEndereço da carteira: {wallet.address}")
    
    try:
        # Verificar saldo
        saldo = wallet.get_balance()
        print(f"Saldo atual: {saldo} XRP")
        
        # Se tiver saldo suficiente, fazer o pagamento
        if saldo > Decimal("10"):
            destination = "rPT1Sjq2YGrBMTttX4GZHjKu9dyfzbpAYe"
            print(f"\nIniciando pagamento de 10 XRP para {destination}")
            
            # Executar o pagamento de forma assíncrona
            loop = asyncio.get_event_loop()
            hash_tx = loop.run_until_complete(wallet.send_payment(destination, Decimal("10")))
            print(f"Pagamento realizado! Hash: {hash_tx}")
        else:
            print("\nSaldo insuficiente para fazer o pagamento.")
            print("Por favor, use o faucet da TestNet para obter XRP de teste:")
            print("https://xrpl.org/xrp-testnet-faucet.html")
            print(f"Seu endereço de carteira: {wallet.address}")
            
    except Exception as e:
        print(f"\nErro: {str(e)}")
    finally:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.close()
        except:
            pass
