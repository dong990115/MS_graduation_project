# centerOffset — 논문 본문에 닫힌 수식 없음.
# "centerOffset is the angular difference between the original heading of an
# incident point and the direction of the vector between the center of the
# roundabout and the incident point" (Ikram et al. 2023, Section III-A).
# 본 구현은 이 산문적 정의를 구현자가 해석한 것임 (see CLAUDE_PLAN.md §1-C).

from operator import ipow
from os import close
from typing_extensions import Literal
from junctionart.roundabout.Generator import Generator
from junctionart.junctions.IncidentPoint import IncidentPoint  # have to to fix
from junctionart.junctions.JunctionBuilder import JunctionBuilder
from junctionart.extensions.ExtendedRoad import ExtendedRoad
from junctionart.junctions.CurveRoadBuilder import CurveRoadBuilder
from junctionart.junctions.StraightRoadBuilder import StraightRoadBuilder
from junctionart.junctions.LaneSides import LaneSides
from junctionart.extensions.CountryCodes import CountryCodes
from junctionart.junctions.ODRHelper import ODRHelper
from junctionart.junctions.ConnectionBuilder import ConnectionBuilder
from junctionart.junctions.Geometry import Geometry
from junctionart.roadgen.layout.PerlinNoise import PerlinNoiseFactory
from junctionart.junctions.RoadLinker import RoadLinker
import pyodrx
import junctionart.extensions as extensions
from junctionart.junctions.RoadBuilder import RoadBuilder
from typing import List, Dict
import random
import math
import numpy as np


class ClassicGenerator(Generator):
    def __init__(self, country=CountryCodes.US, laneWidth=3.5) -> None:
        super().__init__()
        self.curveBuilder = CurveRoadBuilder()
        self.junctionBuilder = JunctionBuilder()
        self.countryCode = country
        self.laneWidth = laneWidth
        self.straightRoadBuilder = StraightRoadBuilder()
        self.roadBuilder = RoadBuilder()
        self.connectionBuilder = ConnectionBuilder()
        self.shoulderWidth = 3.0

    def _addShoulders(self, road, sides='right'):
        """Add shoulder lanes to a road for junction boundary expansion."""
        for ls in road.lanes.lanesections:
            if sides in ('right', 'both'):
                s = pyodrx.Lane(lane_type=pyodrx.LaneType.shoulder,
                                a=self.shoulderWidth)
                s.set_material(surface="concrete")
                ls.add_right_lane(s)
            if sides in ('left', 'both'):
                s = pyodrx.Lane(lane_type=pyodrx.LaneType.shoulder,
                                a=self.shoulderWidth)
                s.set_material(surface="concrete")
                ls.add_left_lane(s)

    @staticmethod
    def _removeRoadMarks(road):
        for ls in road.lanes.lanesections:
            ls.centerlane.roadmark = None
            for lane in ls.rightlanes + ls.leftlanes:
                lane.roadmark = None

    @staticmethod
    def _removeCenterRoadMark(road):
        for ls in road.lanes.lanesections:
            ls.centerlane.roadmark = None

    @staticmethod
    def _setYellowCenterMark(road):
        mark = pyodrx.RoadMark(pyodrx.RoadMarkType.solid, 0.2,
                               color=pyodrx.RoadMarkColor.yellow)
        for ls in road.lanes.lanesections:
            ls.centerlane.roadmark = mark

    @staticmethod
    def _setBrokenLaneMarks(road):
        broken = pyodrx.RoadMark(pyodrx.RoadMarkType.broken, 0.2,
                                 length=3.0, space=3.0,
                                 color=pyodrx.RoadMarkColor.standard)
        solid = pyodrx.RoadMark(pyodrx.RoadMarkType.solid, 0.2,
                                color=pyodrx.RoadMarkColor.standard)
        for ls in road.lanes.lanesections:
            driving_r = [l for l in ls.rightlanes
                         if l.lane_type == pyodrx.LaneType.driving]
            driving_l = [l for l in ls.leftlanes
                         if l.lane_type == pyodrx.LaneType.driving]
            for lanes in (driving_r, driving_l):
                for i, lane in enumerate(lanes):
                    if i < len(lanes) - 1:
                        lane.roadmark = broken
                    else:
                        lane.roadmark = solid

    @staticmethod
    def _setThroughConnectionMarks(throughRoads):
        broken = pyodrx.RoadMark(pyodrx.RoadMarkType.broken, 0.2,
                                 length=3.0, space=3.0,
                                 color=pyodrx.RoadMarkColor.standard)
        solid = pyodrx.RoadMark(pyodrx.RoadMarkType.solid, 0.2,
                                color=pyodrx.RoadMarkColor.standard)
        for road in throughRoads:
            is_inner = road.predecessorOffset == 0
            for ls in road.lanes.lanesections:
                for lane in ls.rightlanes + ls.leftlanes:
                    if lane.lane_type == pyodrx.LaneType.driving:
                        lane.roadmark = broken if is_inner else None

    def generateWithIncidentPointConfiguration(
        self,
        ipConfig: List[Dict],
        firstRoadId=0,
        maxLanePerSide=2,
        minLanePerSide=0,
        skipEndpoint=None,
        odrId=0,
        nCircularLanes=2,
        useCenterOffset=False,
        adaptiveLength=False,
        clearanceFactor=1.2,
        roadDirection='heading',
        distorted=False,
        distortionAmplitude=0.25,
        noiseFrequency=2.0,
        noiseSeed=0,
        overrideRadius=None,
    ):

        incidentPoints = self.parseIncidentPoints(ipConfig)

        self.connectionBuilder.config.dic["default_lane_width"] = self.laneWidth

        # 1. get a circle
        center, radius = self.getCircle(incidentPoints)
        if overrideRadius is not None:
            radius = overrideRadius
        self.center = center
        self.radius = radius

        nSegments = 12

        # 2. make the circular road with segments
        if distorted:
            circularRoads, circularRoadStartPoints = self.getDistortedCircularRoads(
                center, radius, firstRoadId, nLanes=nCircularLanes,
                laneSides=LaneSides.RIGHT, nSegments=nSegments,
                distortionAmplitude=distortionAmplitude,
                noiseFrequency=noiseFrequency,
                noiseSeed=noiseSeed,
            )
        else:
            circularRoads, circularRoadStartPoints = self.getCircularRoads(
                center, radius, firstRoadId, nLanes=nCircularLanes,
                laneSides=LaneSides.RIGHT, nSegments=nSegments,
            )
        for cr in circularRoads:
            self._addShoulders(cr, sides='right')
            self._removeCenterRoadMark(cr)
            self._setBrokenLaneMarks(cr)
        self.createSuccPreRelationBetweenCircularRoads(circularRoads)

        odrName = "TempCircularRoads" + str(odrId)
        odr = extensions.createOdrByPredecessor(
            odrName, circularRoads, [], countryCode=self.countryCode
        )

        odr.updateRoads(circularRoads)
        odr.resetAndReadjust(byPredecessor=True)
        ODRHelper.transform(
            odr,
            startX=circularRoadStartPoints[0].x,
            startY=circularRoadStartPoints[0].y,
            heading=0,
        )

        # Close the ring: link last segment → first segment (after positioning)
        RoadLinker.createExtendedPredSuc(
            predRoad=circularRoads[-1],
            predCp=pyodrx.ContactPoint.end,
            sucRoad=circularRoads[0],
            sucCP=pyodrx.ContactPoint.start,
        )

        # 3. create approach roads FIRST (endpoints needed for segment selection)
        minClearanceFactor = (radius + nCircularLanes * self.laneWidth + 10.0) / radius
        effectiveClearanceFactor = max(clearanceFactor, minClearanceFactor)

        firstApproachRoadId = firstRoadId + len(circularRoads)
        approachRoads, approachEndpoints = self.createApproachRoads(
            incidentPoints, firstApproachRoadId,
            adaptiveLength=adaptiveLength,
            clearanceFactor=effectiveClearanceFactor,
            roadDirection=roadDirection,
        )

        # 4. select ring segments using approach road endpoints (near ring)
        closestCircularRoadIdForIncidentPoints = \
            self.getClosestCircularRoadIdForIncidentPoints(
                approachEndpoints, circularRoadStartPoints
            )

        # 4b. resolve overlapping junctions: keep bridge segments
        nApproaches = len(approachRoads)
        upstreamRoad = {}
        downstreamRoad = {}
        segmentsToRemove = set()
        bridgeSegmentIndices = set()

        for i in range(nApproaches):
            cId = closestCircularRoadIdForIncidentPoints[i]
            upstreamRoad[i] = circularRoads[(cId - 2) % nSegments]
            downstreamRoad[i] = circularRoads[(cId + 1) % nSegments]
            segmentsToRemove.add((cId - 1) % nSegments)
            segmentsToRemove.add(cId)

        sortedOrder = sorted(range(nApproaches),
                             key=lambda i: closestCircularRoadIdForIncidentPoints[i])

        for k in range(len(sortedOrder)):
            i_app = sortedOrder[k]
            j_app = sortedOrder[(k + 1) % len(sortedOrder)]
            ci = closestCircularRoadIdForIncidentPoints[i_app]
            cj = closestCircularRoadIdForIncidentPoints[j_app]
            gap = (cj - ci) % nSegments
            if gap < 3:
                bridgeIdx = (ci + 1) % nSegments
                segmentsToRemove.discard(bridgeIdx)
                bridgeSegmentIndices.add(bridgeIdx)
                upstreamRoad[j_app] = circularRoads[bridgeIdx]

        # 5. determine exit/entry/through/filler lane link configs
        exitLinks, entryLinks, throughLinks, fillerExitLinks, fillerEntryLinks = \
            self.getLaneConfigForConnectionRoads(
                approachRoads, circularRoads, upstreamRoad, downstreamRoad,
            )

        roadDic = self.getRoadDic(approachRoads, circularRoads)

        # 6. create exit connections (upstream end → approach start)
        firstConnectionId = firstApproachRoadId + len(approachRoads)
        exitConnectionRoads = self.getConnectionRoads(
            firstConnectionId, roadDic,
            pyodrx.ContactPoint.end,
            pyodrx.ContactPoint.start,
            exitLinks,
        )

        # 7. create entry connections (approach start → downstream start)
        nextId = firstConnectionId + len(exitConnectionRoads)
        entryConnectionRoads = self.getConnectionRoads(
            nextId, roadDic,
            pyodrx.ContactPoint.start,
            pyodrx.ContactPoint.start,
            entryLinks,
        )

        # 8. create through connections (upstream end → downstream start)
        nextId += len(entryConnectionRoads)
        throughConnectionRoads = self.getConnectionRoads(
            nextId, roadDic,
            pyodrx.ContactPoint.end,
            pyodrx.ContactPoint.start,
            throughLinks,
        )

        # 8b. create filler-exit connections (upstream:-1 end → approach:-1 start)
        nextId += len(throughConnectionRoads)
        fillerExitConnectionRoads = self.getConnectionRoads(
            nextId, roadDic,
            pyodrx.ContactPoint.end,
            pyodrx.ContactPoint.start,
            fillerExitLinks,
        )

        # 8c. create filler-entry connections (approach:1 start → downstream:-1 start)
        nextId += len(fillerExitConnectionRoads)
        fillerEntryConnectionRoads = self.getConnectionRoads(
            nextId, roadDic,
            pyodrx.ContactPoint.start,
            pyodrx.ContactPoint.start,
            fillerEntryLinks,
        )

        # 9. remove deleted ring segments (segmentsToRemove already computed in 4b)
        remainingCircularRoads = [
            road for idx, road in enumerate(circularRoads)
            if idx not in segmentsToRemove
        ]

        # 10. assemble
        nonRingConnectionRoads = (exitConnectionRoads + entryConnectionRoads
                                  + fillerExitConnectionRoads
                                  + fillerEntryConnectionRoads)
        for cr in nonRingConnectionRoads:
            self._removeRoadMarks(cr)
        for cr in throughConnectionRoads:
            self._removeCenterRoadMark(cr)
        self._setThroughConnectionMarks(throughConnectionRoads)

        roads = []
        roads.extend(remainingCircularRoads)
        roads.extend(exitConnectionRoads)
        roads.extend(approachRoads)
        roads.extend(entryConnectionRoads)
        roads.extend(throughConnectionRoads)
        roads.extend(fillerExitConnectionRoads)
        roads.extend(fillerEntryConnectionRoads)

        odr.updateRoads(roads)
        odr = ODRHelper.transform(
            odr=odr,
            startX=circularRoadStartPoints[0].x,
            startY=circularRoadStartPoints[0].y,
            heading=0,
        )

        # remove deleted ring segments from odr (after transform)
        for segIdx in segmentsToRemove:
            delId = str(circularRoads[segIdx].id)
            if delId in odr.roads:
                del odr.roads[delId]

        # 11. Create multi-junction (1 per approach)
        self._createJunctions(
            approachRoads,
            exitConnectionRoads, entryConnectionRoads,
            throughConnectionRoads,
            fillerExitConnectionRoads, fillerEntryConnectionRoads,
            upstreamRoad, downstreamRoad, odr,
        )

        # 12. Shorten bridge segments and recreate affected connection roads
        for bIdx in bridgeSegmentIndices:
            origRoad = circularRoads[bIdx]
            bx, by, bh = origRoad.getPosition(pyodrx.ContactPoint.start)
            shortBridge = self.curveBuilder.createCurveByLength(
                roadId=origRoad.id,
                length=1.0,
                curvature=1.0 / radius,
                n_lanes=nCircularLanes,
                lane_offset=self.laneWidth,
                laneSides=LaneSides.RIGHT,
            )
            self._addShoulders(shortBridge, sides='right')
            self._removeCenterRoadMark(shortBridge)
            self._setBrokenLaneMarks(shortBridge)
            shortBridge.planview.set_start_point(bx, by, bh)
            shortBridge.planview.adjust_geometires()
            shortBridge.predecessor = origRoad.predecessor
            shortBridge.successor = origRoad.successor
            shortBridge.junctionId = origRoad.junctionId
            odr.roads[str(origRoad.id)] = shortBridge

            # Find which approach uses this bridge as upstream (j_app)
            j_app = None
            for i in range(nApproaches):
                if upstreamRoad[i] is origRoad:
                    j_app = i
                    break
            if j_app is None:
                continue

            # Recreate through/exit connections from bridge.end
            juncId = 100 + j_app
            downstream = downstreamRoad[j_app]
            approach = approachRoads[j_app]
            bridgeDic = {
                shortBridge.id: shortBridge,
                downstream.id: downstream,
                approach.id: approach,
            }

            oldThroughOuter = throughConnectionRoads[j_app * 2]
            oldThroughInner = throughConnectionRoads[j_app * 2 + 1]
            oldExit = exitConnectionRoads[j_app]
            oldFillerExit = fillerExitConnectionRoads[j_app]

            throughLinks = [
                (str(shortBridge.id) + ":-1", str(downstream.id) + ":-1"),
                (str(shortBridge.id) + ":-2", str(downstream.id) + ":-2"),
            ]
            newThroughs = self.getConnectionRoads(
                oldThroughOuter.id, bridgeDic,
                pyodrx.ContactPoint.end, pyodrx.ContactPoint.start,
                throughLinks,
            )
            exitLink = [
                (str(shortBridge.id) + ":-2", str(approach.id) + ":-1"),
            ]
            newExits = self.getConnectionRoads(
                oldExit.id, bridgeDic,
                pyodrx.ContactPoint.end, pyodrx.ContactPoint.start,
                exitLink,
            )
            fillerExitLink = [
                (str(shortBridge.id) + ":-1", str(approach.id) + ":-1"),
            ]
            newFillerExits = self.getConnectionRoads(
                oldFillerExit.id, bridgeDic,
                pyodrx.ContactPoint.end, pyodrx.ContactPoint.start,
                fillerExitLink,
            )

            for newRoad in newExits + newFillerExits:
                self._removeRoadMarks(newRoad)
            for newRoad in newThroughs:
                self._removeCenterRoadMark(newRoad)
            self._setThroughConnectionMarks(newThroughs)
            for newRoad in newThroughs:
                newRoad.junctionId = juncId
                bId = newRoad.predecessorOffset
                sx, sy, sh = shortBridge.getLanePosition(bId, pyodrx.ContactPoint.end)
                newRoad.planview.set_start_point(sx, sy, sh)
                newRoad.planview.adjust_geometires()
                odr.roads[str(newRoad.id)] = newRoad

        return odr

    def _createJunctions(self, approachRoads,
                         exitConnectionRoads, entryConnectionRoads,
                         throughConnectionRoads,
                         fillerExitConnectionRoads, fillerEntryConnectionRoads,
                         upstreamRoad, downstreamRoad, odr):
        for i in range(len(approachRoads)):
            juncId = 100 + i

            ringCm2 = upstreamRoad[i]
            ringCp1 = downstreamRoad[i]
            exitConn = exitConnectionRoads[i]
            entryConn = entryConnectionRoads[i]
            throughOuter = throughConnectionRoads[i * 2]
            throughInner = throughConnectionRoads[i * 2 + 1]
            fillerExit = fillerExitConnectionRoads[i]
            fillerEntry = fillerEntryConnectionRoads[i]
            approach = approachRoads[i]

            junction = pyodrx.Junction(f"roundabout_{i}", juncId)

            # connection road의 junctionId 설정
            throughOuter.junctionId = juncId
            throughInner.junctionId = juncId
            exitConn.junctionId = juncId
            entryConn.junctionId = juncId
            fillerExit.junctionId = juncId
            fillerEntry.junctionId = juncId

            # 외부 도로 링크 → junction으로 교체
            ringCm2.updateSuccessor(
                pyodrx.ElementType.junction, juncId)
            ringCp1.updatePredecessor(
                pyodrx.ElementType.junction, juncId)
            approach.clearAllLinks()
            approach.updatePredecessor(
                pyodrx.ElementType.junction, juncId)

            # junction connection 등록 (6가지 경로)
            connThroughOuter = pyodrx.Connection(
                incoming_road=ringCm2.id,
                connecting_road=throughOuter.id,
                contact_point=pyodrx.ContactPoint.start,
            )
            connThroughOuter.add_lanelink(-1, -1)
            junction.add_connection(connThroughOuter)

            connThroughInner = pyodrx.Connection(
                incoming_road=ringCm2.id,
                connecting_road=throughInner.id,
                contact_point=pyodrx.ContactPoint.start,
            )
            connThroughInner.add_lanelink(-2, -1)
            junction.add_connection(connThroughInner)

            connExit = pyodrx.Connection(
                incoming_road=ringCm2.id,
                connecting_road=exitConn.id,
                contact_point=pyodrx.ContactPoint.start,
            )
            connExit.add_lanelink(-2, -1)
            junction.add_connection(connExit)

            connEntry = pyodrx.Connection(
                incoming_road=approach.id,
                connecting_road=entryConn.id,
                contact_point=pyodrx.ContactPoint.start,
            )
            connEntry.add_lanelink(1, -1)
            junction.add_connection(connEntry)

            connFillerExit = pyodrx.Connection(
                incoming_road=ringCm2.id,
                connecting_road=fillerExit.id,
                contact_point=pyodrx.ContactPoint.start,
            )
            connFillerExit.add_lanelink(-1, -1)
            junction.add_connection(connFillerExit)

            connFillerEntry = pyodrx.Connection(
                incoming_road=approach.id,
                connecting_road=fillerEntry.id,
                contact_point=pyodrx.ContactPoint.start,
            )
            connFillerEntry.add_lanelink(1, -1)
            junction.add_connection(connFillerEntry)

            odr.add_junction(junction)


    def getLaneConfigForConnectionRoads(
        self, approachRoads, circularRoads, upstreamRoad, downstreamRoad,
    ):
        """Generate link configs for exit, entry, and through connection roads."""
        exitLinks = []
        entryLinks = []
        throughLinks = []
        fillerExitLinks = []
        fillerEntryLinks = []

        for i in range(len(approachRoads)):
            upstream = upstreamRoad[i]
            downstream = downstreamRoad[i]

            exitLink = (
                str(upstream.id) + ":-2",
                str(approachRoads[i].id) + ":-1",
            )
            entryLink = (
                str(approachRoads[i].id) + ":1",
                str(downstream.id) + ":-2",
            )
            throughLinkOuter = (
                str(upstream.id) + ":-1",
                str(downstream.id) + ":-1",
            )
            throughLinkInner = (
                str(upstream.id) + ":-2",
                str(downstream.id) + ":-2",
            )
            fillerExitLink = (
                str(upstream.id) + ":-1",
                str(approachRoads[i].id) + ":-1",
            )
            fillerEntryLink = (
                str(approachRoads[i].id) + ":1",
                str(downstream.id) + ":-1",
            )
            exitLinks.append(exitLink)
            entryLinks.append(entryLink)
            throughLinks.append(throughLinkOuter)
            throughLinks.append(throughLinkInner)
            fillerExitLinks.append(fillerExitLink)
            fillerEntryLinks.append(fillerEntryLink)

        return exitLinks, entryLinks, throughLinks, fillerExitLinks, fillerEntryLinks

    def getRoadDic(self, straightRoads, circularRoads):
        roadDic = {road.id: road for road in straightRoads}
        for road in circularRoads:
            roadDic[road.id] = road
        return roadDic

    def getConnectionRoads(self, startRoadId, roadDic, cp1, cp2, laneConfig):
        connectionRoads = self.connectionBuilder.createRoadsForRoundaboutLinkConfig(
            startRoadId, roadDic, cp1, cp2, laneConfig
        )
        return connectionRoads

    def getClosestCircularRoadIdForIncidentPoints(
        self, incidentPoints, circularRoadStartPoints
    ):
        closestCircularRoadIdForIncidentPoints = []
        for incidentPoint in incidentPoints:
            incidentPointWithoutHeading = Point(incidentPoint.x, incidentPoint.y)
            bestPoint = circularRoadStartPoints[0]
            bestDistance = self.__distance(incidentPointWithoutHeading, bestPoint)
            for circularRoadStartPoint in circularRoadStartPoints:
                bestPoint = (
                    circularRoadStartPoint
                    if (
                        self.__distance(
                            incidentPointWithoutHeading, circularRoadStartPoint
                        )
                        < bestDistance
                    )
                    else bestPoint
                )
                bestDistance = self.__distance(incidentPointWithoutHeading, bestPoint)

            closestCircularRoadId = circularRoadStartPoints.index(bestPoint)
            closestCircularRoadIdForIncidentPoints.append(closestCircularRoadId)

        return closestCircularRoadIdForIncidentPoints

    @staticmethod
    def computeCenterOffset(ip, center):
        """Signed angular difference between IP heading and radial outward direction.

        Paper does not specify a closed-form formula; this is the implementer's
        interpretation. Returns radians in [-pi, pi]. Positive = CCW shift.
        """
        radialOutward = math.atan2(ip.y - center.y, ip.x - center.x)
        delta = ip.heading - radialOutward
        return math.atan2(math.sin(delta), math.cos(delta))

    def getSegmentByCenterOffset(
        self, incidentPoints, circularRoadStartPoints, center
    ):
        """Select ring segment for each IP using centerOffset angular matching.

        Paper does not specify a closed-form formula; this is the implementer's
        interpretation: argmin_k |angle(seg_k - C) - angle(P - C) - centerOffset|.
        """
        result = []
        for ip in incidentPoints:
            offset = self.computeCenterOffset(ip, center)
            ipAngle = math.atan2(ip.y - center.y, ip.x - center.x)
            targetAngle = ipAngle + offset

            bestIdx = 0
            bestDiff = float('inf')
            for k, sp in enumerate(circularRoadStartPoints):
                segAngle = math.atan2(sp.y - center.y, sp.x - center.x)
                diff = abs(math.atan2(
                    math.sin(targetAngle - segAngle),
                    math.cos(targetAngle - segAngle),
                ))
                if diff < bestDiff:
                    bestDiff = diff
                    bestIdx = k
            result.append(bestIdx)
        return result

    def parseIncidentPoints(self, ipConfig: List[Dict]):
        return [IncidentPoint.parseIncidentPoint(point) for point in ipConfig]

    def createApproachRoads(self, incidentPoints: List[IncidentPoint], firstRoadID,
                            adaptiveLength=False, clearanceFactor=1.2,
                            roadDirection='radial'):
        """Create ONE bidirectional approach road per incident point.

        Road orientation: START near ring, END at IP.
        Lane -1 (right) = outbound (ring → IP).
        Lane +1 (left)  = inbound  (IP → ring).

        roadDirection: 'radial' = toward center, 'heading' = ip.heading.
        adaptiveLength: False = L = dist - r_eff, True = adaptive formula.
        Returns (approachRoads, approachEndpoints) where endpoints are near-ring
        start positions used for segment selection.
        """
        approachRoads = []
        approachEndpoints = []
        r_eff = self.radius * clearanceFactor

        for i, ip in enumerate(incidentPoints):
            if roadDirection == 'heading':
                inwardDir = ip.heading + math.pi
            else:
                inwardDir = math.atan2(
                    self.center.y - ip.y, self.center.x - ip.x
                )

            if adaptiveLength:
                hx = math.cos(inwardDir)
                hy = math.sin(inwardDir)
                vx = self.center.x - ip.x
                vy = self.center.y - ip.y
                t_star = vx * hx + vy * hy
                dist_sq = vx * vx + vy * vy
                p_sq = max(dist_sq - t_star * t_star, 0)
                if p_sq >= r_eff * r_eff:
                    roadLength = max(t_star, 0)
                else:
                    roadLength = max(t_star - math.sqrt(r_eff * r_eff - p_sq), 0)
            else:
                distance = self.__distance(ip, self.center)
                roadLength = max(distance - r_eff, 0)

            startX = ip.x + roadLength * math.cos(inwardDir)
            startY = ip.y + roadLength * math.sin(inwardDir)
            startHeading = inwardDir + math.pi

            approachEndpoints.append(Point(startX, startY))

            roadId = firstRoadID + i
            road = self.straightRoadBuilder.create(
                roadId=roadId,
                length=roadLength,
                n_lanes_left=1, n_lanes_right=1,
                lane_offset=self.laneWidth,
                laneSides=LaneSides.BOTH,
            )
            self._addShoulders(road, sides='both')
            self._setYellowCenterMark(road)

            odrTemp = extensions.createOdrByPredecessor(
                "tempODR_approach" + str(i), [road], [],
                countryCode=self.countryCode,
            )
            ODRHelper.transform(odrTemp, startX, startY, startHeading)

            approachRoads.append(road)

        return approachRoads, approachEndpoints

    def createSuccPreRelationBetweenCircularRoads(self, circularRoads):
        nCircularRoads = len(circularRoads)
        for i in range(nCircularRoads - 1):
            RoadLinker.createExtendedPredSuc(
                predRoad=circularRoads[i],
                predCp=pyodrx.ContactPoint.end,
                sucRoad=circularRoads[i + 1],
                sucCP=pyodrx.ContactPoint.start,
            )

    def getCircularRoads(self, center, radius, firstRoadId, nLanes=2,
                         laneSides=LaneSides.RIGHT, nSegments=10):
        roadLength = 2 * np.pi * radius / nSegments
        curvature = 1 / radius

        circularRoads = []
        circularRoadStartPoints = []

        for i in range(nSegments):
            circularRoad = self.curveBuilder.createCurveByLength(
                roadId=firstRoadId + i,
                length=roadLength,
                curvature=curvature,
                n_lanes=nLanes,
                lane_offset=self.laneWidth,
                laneSides=laneSides,
            )
            odrName = "tempODR_circularRoad" + str(i + 1)

            newHeading = i * (360 / nSegments)
            newX = center.x + radius * math.sin(math.radians(newHeading))
            newY = center.y - radius * math.cos(math.radians(newHeading))

            circularRoadStartPoints.append(Point(newX, newY))
            circularRoads.append(circularRoad)

        return circularRoads, circularRoadStartPoints

    def getDistortedCircularRoads(self, center, radius, firstRoadId, nLanes=2,
                                  laneSides=LaneSides.RIGHT, nSegments=10,
                                  distortionAmplitude=0.25, noiseFrequency=2.0,
                                  noiseSeed=0):
        """Create ring roads with Perlin-distorted radii, connected by ParamPoly3.

        Paper Phase 2 "distorted circle" branch (Fig.3c): Perlin noise shifts
        each segment endpoint radially, then cubic Hermite splines (ParamPoly3)
        connect them instead of perfect arcs.
        """
        rng_state = random.getstate()
        random.seed(noiseSeed)
        pnf = PerlinNoiseFactory(
            dimension=1, octaves=2, tile=(round(noiseFrequency),)
        )

        points = []
        for k in range(nSegments):
            theta_rad = math.radians(k * 360 / nSegments)
            t = k * noiseFrequency / nSegments
            noise_val = pnf(t)
            r_k = radius * (1 + distortionAmplitude * noise_val)
            x_k = center.x + r_k * math.sin(theta_rad)
            y_k = center.y - r_k * math.cos(theta_rad)
            points.append((x_k, y_k))

        random.setstate(rng_state)

        headings = []
        for k in range(nSegments):
            p = (k - 1) % nSegments
            n = (k + 1) % nSegments
            dx = points[n][0] - points[p][0]
            dy = points[n][1] - points[p][1]
            headings.append(math.atan2(dy, dx))

        circularRoads = []
        circularRoadStartPoints = []

        for k in range(nSegments):
            k_next = (k + 1) % nSegments
            x1, y1 = points[k]
            x2, y2 = points[k_next]
            h1 = headings[k]
            h2 = headings[k_next]

            circularRoadStartPoints.append(Point(x1, y1))

            xCoeffs, yCoeffs = Geometry.getCoeffsForParamPoly(
                x1, y1, h1, x2, y2, h2,
                cp1=pyodrx.ContactPoint.end,
                cp2=pyodrx.ContactPoint.start,
            )

            au = xCoeffs[3]
            bu = xCoeffs[2]
            cu = xCoeffs[1]
            du = xCoeffs[0]
            av = yCoeffs[3]
            bv = yCoeffs[2]
            cv = yCoeffs[1]
            dv = yCoeffs[0]

            arc_len = 0.0
            n_steps = 100
            dt = 1.0 / n_steps
            for j in range(n_steps):
                t = (j + 0.5) * dt
                dxdt = bu + 2 * cu * t + 3 * du * t * t
                dydt = bv + 2 * cv * t + 3 * dv * t * t
                arc_len += math.sqrt(dxdt * dxdt + dydt * dydt) * dt

            road = self.curveBuilder.createParamPoly3(
                roadId=firstRoadId + k,
                au=au, bu=bu, cu=cu, du=du,
                av=av, bv=bv, cv=cv, dv=dv,
                prange='normalized',
                length=arc_len,
                n_lanes=nLanes,
                lane_offset=self.laneWidth,
                laneSides=laneSides,
            )

            circularRoads.append(road)

        return circularRoads, circularRoadStartPoints

    def getCircle(self, incidentPoints: List[IncidentPoint]):
        optimalCenter, radius = self.getOptimalCircle(incidentPoints)
        # quality, optimalCenter, radius = self.getRandomizedCircle(incidentPoints, optimalCenter, radius)
        # NOTE : circularRandomizer does not work
        return optimalCenter, radius * 0.4

    def createIntersections(
        self, incidentPoints: List[IncidentPoint], circularRoads: List[ExtendedRoad]
    ):
        return []

    def getOptimalCircle(self, incidentPoints):
        if len(incidentPoints) == 2:
            center = Point(
                (incidentPoints[0].x + incidentPoints[1].x) / 2,
                (incidentPoints[0].y + incidentPoints[1].y) / 2,
            )
            radius = self.__distance(incidentPoints[0], incidentPoints[1]) / 2
            return center, radius

        sum_x = (
            sum_y
        ) = sum_xx = sum_yy = sum_xy = sum_xxy = sum_xyy = sum_xxx = sum_yyy = 0.0
        A = B = C = D = E = 0.0
        x2 = y2 = xy = xDiff = yDiff = 0.0
        for incidentPoint in incidentPoints:
            sum_x += incidentPoint.x
            sum_y += incidentPoint.y
            x2 = incidentPoint.x * incidentPoint.x
            y2 = incidentPoint.y * incidentPoint.y
            xy = incidentPoint.x * incidentPoint.y
            sum_xx += x2
            sum_yy += y2
            sum_xy += xy
            sum_xxy += x2 * incidentPoint.y
            sum_xyy += y2 * incidentPoint.x
            sum_xxx += x2 * incidentPoint.x
            sum_yyy += y2 * incidentPoint.y

        n = len(incidentPoints)
        A = n * sum_xx - sum_x * sum_x
        B = n * sum_xy - sum_x * sum_y
        C = n * sum_yy - sum_y * sum_y
        D = 0.5 * (n * (sum_xyy + sum_xxx) - sum_x * sum_yy - sum_x * sum_xx)
        E = 0.5 * (n * (sum_xxy + sum_yyy) - sum_y * sum_xx - sum_y * sum_yy)

        F = A * C - B * B
        centerX = (D * C - B * E) / F
        centerY = (A * E - B * D) / F
        center = Point(centerX, centerY)

        radius = 10000000
        for i in range(n):
            xDiff = incidentPoints[i].x - centerX
            yDiff = incidentPoints[i].y - centerY
            radius = min(radius, (xDiff * xDiff + yDiff * yDiff) ** 0.5)

        return center, radius
        # returns optimal circle (x, y, r) for the given list of points.

    def getRandomizedCircle(
        self, incidentPoints: List[IncidentPoint], optimalCenter, radius
    ):
        a = random.uniform(0, 2)
        b = random.uniform(0, 2)
        newX = optimalCenter.x * a
        newY = optimalCenter.y * b
        newCenter = Point(newX, newY)

        radius = 1000000
        resultQuality = 0
        for i in range(len(incidentPoints)):
            resultQuality += math.sqrt(
                (incidentPoints[i].x - newX) ** 2 + (incidentPoints[i].y - newY) ** 2
            )
            xDiff = incidentPoints[i].x - newX
            yDiff = incidentPoints[i].y - newY
            radius = min(radius, (xDiff * xDiff + yDiff * yDiff) ** 0.5)

        # radius *= 0.9
        resultQuality -= len(incidentPoints) * (radius)
        resultQuality /= len(incidentPoints)
        return (resultQuality), newCenter, radius

    def __distance(self, p, q):
        return math.sqrt((p.x - q.x) ** 2 + (p.y - q.y) ** 2)


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
