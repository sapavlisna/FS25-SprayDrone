-- Lezení po žebříku vleku běžným pohybem hráče (docs/DRON.md): hra žebříky umí jako spouštěč LadderTrigger (hráč v něm
-- ztratí gravitaci a chůze dopředu / jump ho vynáší), ale jen pro objekty mapy. Tady se stejný LadderTrigger založí nad
-- spouštěčem ladderTrigger z i3d vleku; ten je potomkem kloubu žebříku (ladderHinge), takže se otáčí s ním. Jen klient.

SprayDroneLadder = {}

-- spouštěč žebříku platí do tohoto času skládání vleku (0 = rozloženo, 1 = složeno); sestup hráče do RELEASE_DISTANCE m od něj
SprayDroneLadder.ACTIVE_UNTIL = 0.05
SprayDroneLadder.RELEASE_DISTANCE = 6

function SprayDroneLadder.load(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.ladder = {}
    if not self.isClient or LadderTrigger == nil or CollisionFlag == nil then
        return
    end
    local node = SprayDroneStation.getMappedNode(self, "ladderTrigger")
    if node == nil then
        return
    end
    -- spouštěč musí "vidět" hráče
    if not CollisionFlag.getHasMaskFlagSet(node, CollisionFlag.PLAYER) then
        setCollisionFilterMask(node, bit32.bor(getCollisionFilterMask(node), CollisionFlag.PLAYER))
    end
    spec.ladder.node = node
    SprayDroneLadder.update(self)
end

-- Hráč, který na žebříku (u uzlu node) právě je, z něj sestoupí: spouštěč při vypnutí ani smazání o odchodu nemusí dát vědět.
local function releasePlayer(node)
    local player = g_localPlayer
    if player ~= nil and player.mover ~= nil and player.mover.isOnLadder and entityExists(node)
        and calcDistanceFrom(player.rootNode, node) < SprayDroneLadder.RELEASE_DISTANCE then
        player.mover:setIsOnLadder(false)
    end
end

-- Spouštěč lezení je zapnutý jen u rozloženého vleku: po složení stojí žebřík svisle u boku a vlek jede. Vypíná se odregistrováním
-- callbacku (LadderTrigger:delete = removeTrigger), skrytí uzlu na fyzikální spouštěč nemá vliv.
function SprayDroneLadder.update(self)
    local ladder = self[SprayDroneStation.SPEC_NAME].ladder
    if ladder == nil or ladder.node == nil or self.getFoldAnimTime == nil then
        return
    end
    local active = self:getFoldAnimTime() <= SprayDroneLadder.ACTIVE_UNTIL
    if active == (ladder.trigger ~= nil) then
        return
    end
    if active then
        ladder.trigger = LadderTrigger.new(ladder.node)
    else
        releasePlayer(ladder.node)
        ladder.trigger:delete()
        ladder.trigger = nil
    end
end

function SprayDroneLadder.delete(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local ladder = spec ~= nil and spec.ladder or nil
    if ladder ~= nil and ladder.trigger ~= nil then
        releasePlayer(ladder.node)
        ladder.trigger:delete()
        ladder.trigger = nil
    end
end
